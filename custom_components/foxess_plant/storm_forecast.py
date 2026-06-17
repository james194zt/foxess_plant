"""Google Weather hourly forecast evaluation for StormSafe lead time."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .storm_weather import categories_matching_ha_condition, is_storm_ha_condition_for_types

DEFAULT_FORECAST_LEAD_HOURS = 4


async def async_storm_in_forecast_window(
    hass: HomeAssistant,
    weather_entity_id: str | None,
    lead_hours: int,
    storm_types: list[str] | None = None,
    category_ids: list[str] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """True when a storm-type hour is forecast within the next lead_hours."""
    if not weather_entity_id or lead_hours < 1:
        return False, {"reason": "no_weather_entity"}

    try:
        response = await hass.services.async_call(
            "weather",
            "get_forecasts",
            {"type": "hourly", "entity_id": weather_entity_id},
            blocking=True,
            return_response=True,
        )
    except Exception as err:
        return False, {"reason": "forecast_unavailable", "error": str(err)}

    if not isinstance(response, dict):
        return False, {"reason": "empty_response"}

    block = response.get(weather_entity_id) or next(iter(response.values()), None)
    if not isinstance(block, dict):
        return False, {"reason": "no_forecast_block"}

    forecast = block.get("forecast") or []
    now = dt_util.utcnow()
    lead = max(1, min(int(lead_hours), 48))
    next_storm: dict[str, Any] | None = None

    for row in forecast:
        if not isinstance(row, dict):
            continue
        when = _parse_forecast_time(row.get("datetime"))
        if when is None:
            continue
        hours_until = (when - now).total_seconds() / 3600.0
        if hours_until < 0:
            continue
        if hours_until > lead:
            continue
        condition = row.get("condition")
        cond_str = str(condition) if condition else None
        if is_storm_ha_condition_for_types(cond_str, storm_types):
            if next_storm is None or hours_until < next_storm["hours_until"]:
                matched = categories_matching_ha_condition(
                    cond_str,
                    category_ids=category_ids,
                    storm_types=storm_types,
                )
                next_storm = {
                    "hours_until": round(hours_until, 1),
                    "datetime": when.isoformat(),
                    "condition": condition,
                    "matched_categories": matched,
                }

    if next_storm:
        return True, {"reason": "forecast_storm", "next_storm": next_storm, "lead_hours": lead}
    return False, {"reason": "clear", "lead_hours": lead, "hours_checked": lead}


def _parse_forecast_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return dt_util.as_utc(value) if value.tzinfo else value.replace(tzinfo=dt_util.UTC)
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        return None
    return dt_util.as_utc(parsed) if parsed.tzinfo else parsed.replace(tzinfo=dt_util.UTC)
