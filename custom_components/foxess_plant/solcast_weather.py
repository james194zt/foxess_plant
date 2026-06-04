"""Parse Solcast radiation/weather data for overview header and StormSafe."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_STORM_SOLCAST_CAPE_THRESHOLD,
    DEFAULT_STORM_SOLCAST_PRECIP_MM_H,
    DEFAULT_STORM_SOLCAST_WEATHER_KEYWORDS,
)

SOLCAST_DOCS_URL = "https://docs.solcast.com.au/"


def _first_series_row(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    for key in ("estimated_actuals", "forecasts", "weather_data", "data"):
        block = payload.get(key)
        if isinstance(block, list) and block:
            row = block[0]
            return row if isinstance(row, dict) else None
    return None


def _normalize_weather_type(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _weather_icon_from_solcast(weather_type: str | None, cloud_opacity: Any = None) -> str:
    if weather_type:
        token = weather_type.lower().replace("-", " ").replace("_", " ")
        if any(k in token for k in ("thunder", "storm", "tornado", "hurricane")):
            return "storm"
        if any(k in token for k in ("rain", "shower", "drizzle")):
            return "rain"
        if any(k in token for k in ("snow", "sleet", "hail", "blizzard")):
            return "snow"
        if any(k in token for k in ("fog", "mist", "haze")):
            return "fog"
        if "wind" in token:
            return "wind"
        if "mostly cloudy" in token or "overcast" in token:
            return "partly-cloudy"
        if "partly" in token or "intermittent" in token:
            return "partly-cloudy"
        if "cloud" in token:
            return "cloudy"
        if any(k in token for k in ("clear", "sunny", "fair")):
            return "sunny"
    try:
        opacity = float(cloud_opacity)
    except (TypeError, ValueError):
        opacity = None
    if opacity is not None:
        if opacity >= 85:
            return "cloudy"
        if opacity >= 40:
            return "partly-cloudy"
        if opacity >= 0:
            return "sunny"
    return "unknown"


def is_storm_solcast_row(
    row: dict[str, Any],
    *,
    weather_keywords: frozenset[str] | None = None,
    cape_threshold: float = DEFAULT_STORM_SOLCAST_CAPE_THRESHOLD,
    precip_threshold: float = DEFAULT_STORM_SOLCAST_PRECIP_MM_H,
) -> bool:
    """True when a Solcast forecast/live row indicates severe weather."""
    keywords = weather_keywords or DEFAULT_STORM_SOLCAST_WEATHER_KEYWORDS
    weather_type = _normalize_weather_type(row.get("weather_type"))
    if weather_type:
        lowered = weather_type.lower()
        if any(kw in lowered for kw in keywords):
            return True
    try:
        cape = float(row.get("cape"))
        if cape >= cape_threshold:
            return True
    except (TypeError, ValueError):
        pass
    try:
        precip = float(row.get("precipitation_rate"))
        if precip >= precip_threshold:
            return True
    except (TypeError, ValueError):
        pass
    return False


def parse_live_overview(live_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    row = _first_series_row(live_payload)
    if not row:
        return None
    weather_type = _normalize_weather_type(row.get("weather_type"))
    air_temp = row.get("air_temp")
    temperature = None
    if air_temp is not None:
        try:
            temperature = float(air_temp)
        except (TypeError, ValueError):
            temperature = None
    icon_key = _weather_icon_from_solcast(weather_type, row.get("cloud_opacity"))
    label = weather_type or "Weather"
    if icon_key == "cloudy" and not weather_type:
        label = "Cloudy"
    elif icon_key == "partly-cloudy" and not weather_type:
        label = "Partly cloudy"
    elif icon_key == "sunny" and not weather_type:
        label = "Clear"
    return {
        "temperature": temperature,
        "temperature_unit": "°C",
        "temperature_display": f"{round(temperature)}°C" if temperature is not None else None,
        "condition_label": label,
        "condition_type": weather_type,
        "icon_key": icon_key,
        "source": "solcast_live",
        "period_end": row.get("period_end"),
        "cloud_opacity": row.get("cloud_opacity"),
        "precipitation_rate": row.get("precipitation_rate"),
        "cape": row.get("cape"),
    }


def storm_in_solcast_forecast(
    forecast_payload: dict[str, Any] | None,
    *,
    lead_hours: int,
    weather_keywords: frozenset[str] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """True when storm conditions appear within lead_hours in Solcast forecast."""
    if not forecast_payload:
        return False, {"reason": "no_solcast_forecast"}
    rows = forecast_payload.get("forecasts")
    if not isinstance(rows, list):
        return False, {"reason": "no_forecast_rows"}
    now = dt_util.utcnow()
    lead = max(1, min(int(lead_hours), 48))
    next_storm: dict[str, Any] | None = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        when = _parse_period_end(row.get("period_end"))
        if when is None:
            continue
        hours_until = (when - now).total_seconds() / 3600.0
        if hours_until < 0 or hours_until > lead:
            continue
        if is_storm_solcast_row(row, weather_keywords=weather_keywords):
            if next_storm is None or hours_until < next_storm["hours_until"]:
                next_storm = {
                    "hours_until": round(hours_until, 1),
                    "period_end": when.isoformat(),
                    "weather_type": row.get("weather_type"),
                    "cape": row.get("cape"),
                    "precipitation_rate": row.get("precipitation_rate"),
                }
    if next_storm:
        return True, {"reason": "solcast_forecast_storm", "next_storm": next_storm, "lead_hours": lead}
    return False, {"reason": "clear", "lead_hours": lead}


def read_overview_from_solcast_cache(cache: dict[str, Any] | None) -> dict[str, Any] | None:
    if not cache:
        return None
    live = cache.get("live")
    overview = parse_live_overview(live if isinstance(live, dict) else None)
    if overview:
        overview["provider"] = "solcast"
    return overview


def is_storm_solcast_live(cache: dict[str, Any] | None) -> bool:
    if not cache:
        return False
    live = cache.get("live")
    row = _first_series_row(live if isinstance(live, dict) else None)
    return bool(row and is_storm_solcast_row(row))


def resolve_coordinates(hass: HomeAssistant, solcast: Any) -> tuple[float, float]:
    lat = getattr(solcast, "latitude", None)
    lon = getattr(solcast, "longitude", None)
    if lat is not None and lon is not None:
        return float(lat), float(lon)
    return float(hass.config.latitude), float(hass.config.longitude)


def _parse_period_end(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return dt_util.as_utc(value) if value.tzinfo else value.replace(tzinfo=dt_util.UTC)
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        return None
    return dt_util.as_utc(parsed) if parsed.tzinfo else parsed.replace(tzinfo=dt_util.UTC)
