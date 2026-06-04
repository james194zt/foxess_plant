"""Solcast polling schedule, quota, and coordinator helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_event_date, get_astral_location
from homeassistant.util import dt as dt_util

from .const import (
    SOLCAST_AUTO_UPDATE_ALL_DAY,
    SOLCAST_AUTO_UPDATE_DAYLIGHT,
    SOLCAST_MIN_POLL_INTERVAL,
    SOLCAST_POLL_END_BEFORE_SUNSET,
)
from .models import PlantConfig, SolcastConfig
from .solcast_api import SolcastApiClient, SolcastApiError
from .solcast_pv import (
    build_rooftop_pv_requests,
    forecast_hours_until_local_midnight,
    parse_detailed_forecast,
    rooftop_requests_summary,
)
from .solcast_unmetered import DEFAULT_UNMETERED_TEST_LOCATION, resolve_unmetered_location
from .solcast_weather import parse_live_overview, resolve_coordinates

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


def get_today_poll_window(hass: HomeAssistant) -> tuple[datetime, datetime] | None:
    """Today's sunrise and last scheduled poll (sunset minus buffer), in local time."""
    try:
        location = get_astral_location(hass)
        now = dt_util.now()
        sunrise = get_astral_event_date(location, SUN_EVENT_SUNRISE, now)
        sunset = get_astral_event_date(location, SUN_EVENT_SUNSET, now)
    except (TypeError, ValueError, KeyError):
        return None
    if sunrise is None or sunset is None:
        return None
    sunrise_local = dt_util.as_local(sunrise)
    sunset_local = dt_util.as_local(sunset)
    poll_end = sunset_local - SOLCAST_POLL_END_BEFORE_SUNSET
    if poll_end <= sunrise_local:
        poll_end = sunset_local
    return sunrise_local, poll_end


def effective_poll_window_hours(hass: HomeAssistant, solcast: SolcastConfig) -> float:
    """Hours between sunrise and (sunset − buffer), or 24h for all-day mode."""
    if solcast.auto_update == SOLCAST_AUTO_UPDATE_ALL_DAY:
        return 24.0
    window = get_today_poll_window(hass)
    if not window:
        return 12.0
    sunrise, poll_end = window
    hours = (poll_end - sunrise).total_seconds() / 3600.0
    return max(1.0, hours)


def is_in_poll_window(hass: HomeAssistant, solcast: SolcastConfig) -> bool:
    """True when automatic PV polling is allowed (daylight window or 24h mode)."""
    if solcast.auto_update == SOLCAST_AUTO_UPDATE_ALL_DAY:
        return True
    window = get_today_poll_window(hass)
    if not window:
        return is_daylight(hass)
    sunrise, poll_end = window
    now = dt_util.now()
    return sunrise <= now < poll_end


def should_poll_now(hass: HomeAssistant, solcast: SolcastConfig) -> bool:
    if not solcast.enabled or not solcast.api_key_configured():
        return False
    return is_in_poll_window(hass, solcast)


def min_poll_interval(
    hass: HomeAssistant,
    solcast: SolcastConfig,
    *,
    pv_calls: int = 1,
) -> timedelta:
    """Space refreshes so API quota spans the poll window (daylight or 24h).

    Example: 10 h window, limit 10, 2 API calls per refresh → 120 min between refreshes.
    """
    limit = max(1, solcast.api_limit)
    calls = max(1, pv_calls)
    hours = effective_poll_window_hours(hass, solcast)
    interval_hours = (hours * calls) / limit
    minutes = max(
        int(SOLCAST_MIN_POLL_INTERVAL.total_seconds() // 60),
        int(interval_hours * 60),
    )
    return timedelta(minutes=minutes)


def solcast_poll_schedule(
    hass: HomeAssistant,
    solcast: SolcastConfig,
    *,
    pv_calls: int = 1,
) -> dict[str, Any]:
    """Human/panel-facing schedule derived from HA sun position."""
    window = get_today_poll_window(hass)
    interval = min_poll_interval(hass, solcast, pv_calls=pv_calls)
    now = dt_util.now()
    if solcast.auto_update == SOLCAST_AUTO_UPDATE_ALL_DAY:
        return {
            "mode": SOLCAST_AUTO_UPDATE_ALL_DAY,
            "window_hours": 24.0,
            "interval_minutes": int(interval.total_seconds() // 60),
            "in_window": True,
        }
    if not window:
        return {
            "mode": SOLCAST_AUTO_UPDATE_DAYLIGHT,
            "window_hours": effective_poll_window_hours(hass, solcast),
            "interval_minutes": int(interval.total_seconds() // 60),
            "in_window": is_daylight(hass),
            "sunrise": None,
            "poll_until": None,
        }
    sunrise, poll_end = window
    return {
        "mode": SOLCAST_AUTO_UPDATE_DAYLIGHT,
        "window_hours": round((poll_end - sunrise).total_seconds() / 3600.0, 1),
        "interval_minutes": int(interval.total_seconds() // 60),
        "in_window": sunrise <= now < poll_end,
        "sunrise": sunrise.isoformat(),
        "poll_until": poll_end.isoformat(),
        "sunset_buffer_minutes": int(SOLCAST_POLL_END_BEFORE_SUNSET.total_seconds() // 60),
    }


def solcast_status_dict(
    solcast: SolcastConfig,
    cache: dict[str, Any] | None,
    *,
    plant: PlantConfig | None = None,
    hass: HomeAssistant | None = None,
) -> dict[str, Any]:
    reset_api_quota_if_needed(solcast)
    out = solcast.to_dict(include_api_key=False)
    out["api_remaining"] = api_remaining(solcast)
    out["coordinates_configured"] = solcast.coordinates_configured()
    if solcast.latitude is not None and solcast.longitude is not None:
        out["coordinates"] = {
            "latitude": solcast.latitude,
            "longitude": solcast.longitude,
        }
    if plant is not None:
        out["pv_requests"] = rooftop_requests_summary(plant)
        if hass is not None:
            pv_calls = max(1, len(build_rooftop_pv_requests(plant.pv_config)) or 1)
            out["poll_schedule"] = solcast_poll_schedule(hass, solcast, pv_calls=pv_calls)
    if cache:
        out["cache_updated_at"] = cache.get("updated_at")
        pv_parsed = cache.get("pv_forecast_parsed")
        if isinstance(pv_parsed, dict):
            out["pv_forecast_available"] = bool(pv_parsed.get("detailed_forecast"))
            out["detailed_forecast"] = pv_parsed.get("detailed_forecast") or []
            out["detailed_forecast_by_site"] = pv_parsed.get("detailed_forecast_by_site") or {}
            out["pv_power_now_kw"] = pv_parsed.get("power_now_kw")
            out["pv_energy_remaining_kwh"] = pv_parsed.get("energy_remaining_kwh")
            out["pv_forecast_periods"] = pv_parsed.get("period_count", 0)
    return out


async def _fetch_rooftop_pv_forecasts(
    hass: HomeAssistant,
    plant: PlantConfig,
    client: SolcastApiClient,
    *,
    lat: float,
    lon: float,
) -> dict[str, Any] | None:
    requests = build_rooftop_pv_requests(plant.pv_config)
    if not requests:
        return None
    hours = forecast_hours_until_local_midnight(hass)
    period = plant.solcast.period
    payloads: list[tuple[str, dict[str, Any]]] = []
    for req in requests:
        try:
            data = await client.forecast_rooftop_pv_power(
                latitude=lat,
                longitude=lon,
                capacity_kw=req.capacity_kw,
                tilt=req.tilt,
                azimuth=req.azimuth,
                loss_factor=req.loss_factor,
                period=period,
                hours=hours,
            )
            payloads.append((req.label, data))
        except SolcastApiError as err:
            _LOGGER.warning("Solcast PV forecast failed for %s: %s", req.label, err)
    if not payloads:
        return None
    return parse_detailed_forecast(payloads)


async def async_refresh_solcast(
    hass: HomeAssistant,
    plant: PlantConfig,
    cache: dict[str, Any],
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Fetch Solcast rooftop PV forecast only (weather/StormSafe use Google Weather)."""
    solcast = plant.solcast
    reset_api_quota_if_needed(solcast)
    if not solcast.enabled or not solcast.api_key_configured():
        return cache
    if not solcast.fetch_pv_forecast:
        return cache
    requests = build_rooftop_pv_requests(plant.pv_config)
    if not requests:
        return cache
    if not force and not should_poll_now(hass, solcast):
        return cache

    pv_calls = len(requests)
    last_at = cache.get("updated_at")
    if last_at and not force:
        try:
            parsed = dt_util.parse_datetime(str(last_at))
            if parsed is not None:
                parsed = dt_util.as_utc(parsed) if parsed.tzinfo else parsed.replace(tzinfo=dt_util.UTC)
                if dt_util.utcnow() - parsed < min_poll_interval(
                    hass, solcast, pv_calls=pv_calls
                ):
                    return cache
        except (TypeError, ValueError):
            pass

    if not can_consume_api(solcast, pv_calls):
        solcast.last_error = "Daily API limit reached"
        return cache

    lat, lon = resolve_coordinates(hass, solcast)
    client = SolcastApiClient(hass, api_key=solcast.api_key or "")
    try:
        parsed = await _fetch_rooftop_pv_forecasts(hass, plant, client, lat=lat, lon=lon)
    except SolcastApiError as err:
        solcast.last_error = str(err)
        _LOGGER.warning("Solcast PV forecast fetch failed: %s", err)
        return cache

    if parsed:
        record_api_use(solcast, pv_calls)
        cache["pv_forecast_parsed"] = parsed
        cache["pv_forecast_fetched_at"] = dt_util.utcnow().isoformat()
        cache["coordinates"] = {"latitude": lat, "longitude": lon}
        solcast.last_error = None

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

