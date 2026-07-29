"""Hybrid daily export kWh for Octopus Analysis (Octopus HH → Glow → Fox)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")

EXPORT_SOURCE_OCTOPUS = "octopus"
EXPORT_SOURCE_GLOW = "glow"
EXPORT_SOURCE_FOX = "fox"


def _uk_date_key(ms: float | int) -> str | None:
    try:
        local = datetime.fromtimestamp(float(ms) / 1000.0, tz=UK_TZ)
    except (TypeError, ValueError, OSError, OverflowError):
        return None
    return local.date().isoformat()


def octopus_export_has_readings(rows: list[dict[str, Any]] | None, *, days: int = 14) -> bool:
    """True when stored Octopus export half-hours include usable kWh in the window."""
    if not rows:
        return False
    now = dt_util.now(UK_TZ)
    cutoff_ms = int((now - timedelta(days=max(1, int(days)))).timestamp() * 1000)
    for row in rows:
        try:
            start_ms = int(row.get("start_ms") or 0)
            kwh = float(row.get("kwh") or 0)
        except (TypeError, ValueError):
            continue
        if start_ms >= cutoff_ms and kwh > 0:
            return True
    return False


def daily_max_by_uk_date(points: list[dict[str, float]]) -> dict[str, float]:
    """Max sensor value seen on each UK local calendar day."""
    by_date: dict[str, float] = {}
    for point in points or []:
        try:
            t_ms = float(point["t"])
            value = float(point["v"])
        except (KeyError, TypeError, ValueError):
            continue
        date_key = _uk_date_key(t_ms)
        if not date_key:
            continue
        prev = by_date.get(date_key)
        if prev is None or value > prev:
            by_date[date_key] = value
    return by_date


def daily_kwh_from_cumulative_max(daily_max: dict[str, float]) -> list[dict[str, Any]]:
    """Turn day-end cumulative totals into per-day export kWh (non-negative deltas)."""
    dates = sorted(daily_max.keys())
    out: list[dict[str, Any]] = []
    for i, date_key in enumerate(dates):
        if i == 0:
            continue
        prev = daily_max[dates[i - 1]]
        cur = daily_max[date_key]
        delta = cur - prev
        if delta < 0:
            # Meter reset or rollover — skip that day rather than inventing a spike.
            continue
        out.append({"date": date_key, "kwh": round(max(0.0, delta), 3)})
    return out


def daily_kwh_from_today_sensor_max(daily_max: dict[str, float]) -> list[dict[str, Any]]:
    """Daily-resetting sensors (Fox feed_in_energy_today): day max is that day's export."""
    return [
        {"date": date_key, "kwh": round(float(daily_max[date_key]), 3)}
        for date_key in sorted(daily_max.keys())
        if float(daily_max[date_key]) > 0
    ]


def expand_daily_kwh_to_half_hours(
    daily: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Spread each day's kWh evenly across 48 half-hours for rate joins / charts."""
    rows: list[dict[str, Any]] = []
    slot_ms = 30 * 60 * 1000
    for item in daily or []:
        date_key = str(item.get("date") or "").strip()
        try:
            kwh = float(item.get("kwh") or 0)
        except (TypeError, ValueError):
            continue
        if not date_key or kwh <= 0:
            continue
        try:
            day = datetime.fromisoformat(date_key).date()
        except ValueError:
            continue
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=UK_TZ)
        start_ms = int(day_start.timestamp() * 1000)
        per = round(kwh / 48.0, 6)
        for i in range(48):
            slot_start = start_ms + i * slot_ms
            rows.append(
                {
                    "start": datetime.fromtimestamp(slot_start / 1000.0, tz=UK_TZ).isoformat(),
                    "end": datetime.fromtimestamp((slot_start + slot_ms) / 1000.0, tz=UK_TZ).isoformat(),
                    "start_ms": slot_start,
                    "end_ms": slot_start + slot_ms,
                    "kwh": per,
                    "source": item.get("source"),
                }
            )
    rows.sort(key=lambda r: int(r["start_ms"]))
    return rows


async def async_history_points_for_entity(
    hass: Any,
    entity_id: str,
    *,
    days: int = 16,
) -> list[dict[str, float]]:
    """Recorder history points for one entity over recent days."""
    if not entity_id:
        return []
    from .websocket_api import _fetch_history_points

    end = dt_util.utcnow()
    start = end - timedelta(days=max(2, int(days) + 2))
    try:
        history_map = await hass.async_add_executor_job(
            _fetch_history_points,
            hass,
            start,
            end,
            [entity_id],
            False,
        )
    except Exception as err:  # noqa: BLE001 — recorder may be unavailable
        _LOGGER.debug("Export hybrid history failed for %s: %s", entity_id, err)
        return []
    return list(history_map.get(entity_id) or [])


async def async_daily_export_from_glow_cumulative(
    hass: Any,
    entity_id: str | None,
    *,
    days: int = 14,
) -> list[dict[str, Any]]:
    if not entity_id:
        return []
    points = await async_history_points_for_entity(hass, entity_id, days=days + 2)
    daily_max = daily_max_by_uk_date(points)
    daily = daily_kwh_from_cumulative_max(daily_max)
    return daily[-max(1, int(days)) :]


async def async_daily_export_from_fox_today(
    hass: Any,
    entity_id: str | None,
    *,
    days: int = 14,
) -> list[dict[str, Any]]:
    if not entity_id:
        return []
    points = await async_history_points_for_entity(hass, entity_id, days=days + 1)
    daily_max = daily_max_by_uk_date(points)
    daily = daily_kwh_from_today_sensor_max(daily_max)
    return daily[-max(1, int(days)) :]


async def async_resolve_hybrid_export_rows(
    hass: Any,
    *,
    octopus_export_rows: list[dict[str, Any]] | None,
    glow_export_cumulative_entity_id: str | None = None,
    fox_export_today_entity_id: str | None = None,
    days: int = 14,
) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """Return (half-hour rows, source tag, soft note). Prefer Octopus HH when present."""
    if octopus_export_has_readings(octopus_export_rows, days=days):
        return list(octopus_export_rows or []), EXPORT_SOURCE_OCTOPUS, None

    glow_daily = await async_daily_export_from_glow_cumulative(
        hass, glow_export_cumulative_entity_id, days=days
    )
    if any(float(d.get("kwh") or 0) > 0 for d in glow_daily):
        for row in glow_daily:
            row["source"] = EXPORT_SOURCE_GLOW
        return (
            expand_daily_kwh_to_half_hours(glow_daily),
            EXPORT_SOURCE_GLOW,
            "Octopus half-hourly export not in yet — using Glow smart-meter cumulative daily deltas",
        )

    fox_daily = await async_daily_export_from_fox_today(
        hass, fox_export_today_entity_id, days=days
    )
    if any(float(d.get("kwh") or 0) > 0 for d in fox_daily):
        for row in fox_daily:
            row["source"] = EXPORT_SOURCE_FOX
        return (
            expand_daily_kwh_to_half_hours(fox_daily),
            EXPORT_SOURCE_FOX,
            "Octopus half-hourly export not in yet — using Fox inverter daily feed-in",
        )

    note = (
        "No export kWh yet from Octopus half-hours, Glow cumulative history, or Fox feed-in today"
    )
    return [], None, note
