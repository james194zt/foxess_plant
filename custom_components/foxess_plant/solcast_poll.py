"""Solcast polling schedule, quota, and coordinator helpers."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import SOLCAST_AUTO_UPDATE_ALL_DAY, SOLCAST_AUTO_UPDATE_DAYLIGHT
from .models import PlantConfig, PvSystemConfig, SolcastConfig
from .solcast_api import SolcastApiClient, SolcastApiError
from .solcast_unmetered import DEFAULT_UNMETERED_TEST_LOCATION, resolve_unmetered_location
from .solcast_weather import (
    is_storm_solcast_live,
    parse_live_overview,
    resolve_coordinates,
    storm_in_solcast_forecast,
)

_LOGGER = logging.getLogger(__name__)


def _today_utc() -> str:
    return dt_util.utcnow().date().isoformat()


def reset_api_quota_if_needed(solcast: SolcastConfig) -> None:
    today = _today_utc()
    if solcast.api_used_date != today:
        solcast.api_used_date = today
        solcast.api_used_today = 0


def api_remaining(solcast: SolcastConfig) -> int:
    reset_api_quota_if_needed(solcast)
    return max(0, solcast.api_limit - solcast.api_used_today)


def can_consume_api(solcast: SolcastConfig, count: int = 1) -> bool:
    reset_api_quota_if_needed(solcast)
    return solcast.api_used_today + count <= solcast.api_limit


def record_api_use(solcast: SolcastConfig, count: int = 1) -> None:
    reset_api_quota_if_needed(solcast)
    solcast.api_used_today += count


def is_daylight(hass: HomeAssistant) -> bool:
    sun = hass.states.get("sun.sun")
    if sun is None:
        return True
    return sun.state == "above_horizon"


def should_poll_now(hass: HomeAssistant, solcast: SolcastConfig) -> bool:
    if not solcast.enabled or not solcast.api_key_configured():
        return False
    if solcast.auto_update == SOLCAST_AUTO_UPDATE_ALL_DAY:
        return True
    if solcast.auto_update == SOLCAST_AUTO_UPDATE_DAYLIGHT:
        return is_daylight(hass)
    return False


def min_poll_interval(solcast: SolcastConfig) -> timedelta:
    """Spread daily quota evenly across 24h or ~12h daylight window."""
    hours = 24 if solcast.auto_update == SOLCAST_AUTO_UPDATE_ALL_DAY else 12
    limit = max(1, solcast.api_limit)
    minutes = max(30, int((hours * 60) / limit))
    return timedelta(minutes=minutes)


def pv_capacity_kw(pv_config: PvSystemConfig) -> float:
    total_w = 0.0
    for string in (pv_config.pv1, pv_config.pv2):
        if not string.enabled:
            continue
        total_w += string.effective_dc_w
    if total_w <= 0:
        total_w = pv_config.pv1.nameplate_dc_w or 5000.0
    return max(0.5, total_w / 1000.0)


def solcast_status_dict(solcast: SolcastConfig, cache: dict[str, Any] | None) -> dict[str, Any]:
    reset_api_quota_if_needed(solcast)
    out = solcast.to_dict(include_api_key=False)
    out["api_remaining"] = api_remaining(solcast)
    out["coordinates"] = {
        "latitude": solcast.latitude,
        "longitude": solcast.longitude,
    }
    if cache:
        out["cache_updated_at"] = cache.get("updated_at")
        live = parse_live_overview(cache.get("live"))
        if live:
            out["live_summary"] = {
                "condition_label": live.get("condition_label"),
                "temperature_display": live.get("temperature_display"),
                "icon_key": live.get("icon_key"),
            }
    return out


async def async_refresh_solcast(
    hass: HomeAssistant,
    plant: PlantConfig,
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Fetch Solcast live (+ optional forecast) within daily API quota."""
    solcast = plant.solcast
    reset_api_quota_if_needed(solcast)
    if not solcast.enabled or not solcast.api_key_configured():
        return cache
    if not force and not should_poll_now(hass, solcast):
        return cache

    last_at = cache.get("updated_at")
    if last_at and not force:
        try:
            parsed = dt_util.parse_datetime(str(last_at))
            if parsed is not None:
                parsed = dt_util.as_utc(parsed) if parsed.tzinfo else parsed.replace(tzinfo=dt_util.UTC)
                if dt_util.utcnow() - parsed < min_poll_interval(solcast):
                    return cache
        except (TypeError, ValueError):
            pass

    if not can_consume_api(solcast, 1):
        solcast.last_error = "Daily API limit reached"
        return cache

    lat, lon = resolve_coordinates(hass, solcast)
    client = SolcastApiClient(hass, api_key=solcast.api_key or "")
    try:
        live = await client.live_radiation_and_weather(
            latitude=lat,
            longitude=lon,
            period=solcast.period,
        )
        record_api_use(solcast, 1)
        cache["live"] = live
        cache["coordinates"] = {"latitude": lat, "longitude": lon}
        solcast.last_error = None
    except SolcastApiError as err:
        solcast.last_error = str(err)
        _LOGGER.warning("Solcast live fetch failed: %s", err)
        return cache

    need_forecast = plant.storm_prep.enabled and plant.storm_prep.use_forecast_lead
    if need_forecast and can_consume_api(solcast, 1):
        try:
            forecast = await client.forecast_radiation_and_weather(
                latitude=lat,
                longitude=lon,
                hours=max(1, min(plant.storm_prep.forecast_lead_hours, 48)),
                period=solcast.period,
            )
            record_api_use(solcast, 1)
            cache["forecast_weather"] = forecast
        except SolcastApiError as err:
            _LOGGER.debug("Solcast forecast weather fetch failed: %s", err)

    cache["updated_at"] = dt_util.utcnow().isoformat()
    solcast.last_fetch_at = cache["updated_at"]
    return cache


async def async_test_solcast_connection(
    hass: HomeAssistant,
    solcast: SolcastConfig,
    *,
    unmetered_name: str | None = None,
) -> dict[str, Any]:
    """Verify API key using a Solcast unmetered location (does not use daily quota)."""
    if not solcast.api_key_configured():
        return {"test_ok": False, "error": "Solcast API key is not configured"}

    label, lat, lon = resolve_unmetered_location(unmetered_name or DEFAULT_UNMETERED_TEST_LOCATION)
    client = SolcastApiClient(hass, api_key=solcast.api_key or "")
    try:
        live = await client.live_radiation_and_weather(
            latitude=lat,
            longitude=lon,
            period=solcast.period,
        )
    except SolcastApiError as err:
        solcast.last_error = str(err)
        return {
            "test_ok": False,
            "error": str(err),
            "test_location": label,
            "test_unmetered": True,
            "quota_charged": False,
        }

    overview = parse_live_overview(live)
    solcast.last_error = None
    return {
        "test_ok": True,
        "test_location": label,
        "test_unmetered": True,
        "quota_charged": False,
        "test_coordinates": {"latitude": lat, "longitude": lon},
        "live_summary": (
            {
                "condition_label": overview.get("condition_label"),
                "temperature_display": overview.get("temperature_display"),
                "icon_key": overview.get("icon_key"),
            }
            if overview
            else None
        ),
    }


def evaluate_solcast_storm_forecast(
    plant: PlantConfig,
    cache: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any]]:
    if not cache or not plant.storm_prep.use_forecast_lead:
        return False, {"reason": "solcast_forecast_disabled"}
    return storm_in_solcast_forecast(
        cache.get("forecast_weather"),
        lead_hours=plant.storm_prep.forecast_lead_hours,
    )


def evaluate_solcast_storm_live(cache: dict[str, Any] | None) -> bool:
    return is_storm_solcast_live(cache)
