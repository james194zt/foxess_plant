"""Detect local PWS / Ecowitt sensors for Performance weather mapping."""

from __future__ import annotations

from typing import Any

# Logical roles Performance (and related weather) can map.
WEATHER_SENSOR_ROLES: tuple[str, ...] = (
    "wind_speed_entity_id",
    "wind_gust_entity_id",
    "precipitation_entity_id",
    "dew_point_entity_id",
    "visibility_entity_id",
    "outdoor_temp_entity_id",
    "humidity_entity_id",
    "solar_radiation_entity_id",
)

ROLE_LABELS = {
    "wind_speed_entity_id": "Wind speed",
    "wind_gust_entity_id": "Wind gust",
    "precipitation_entity_id": "Precipitation rate",
    "dew_point_entity_id": "Dew point",
    "visibility_entity_id": "Visibility",
    "outdoor_temp_entity_id": "Outdoor temperature",
    "humidity_entity_id": "Humidity",
    "solar_radiation_entity_id": "Solar radiation",
}

# Preferred Ecowitt / GW2000A entity-id suffixes (most specific first).
_PREFERRED_SUFFIXES: dict[str, tuple[str, ...]] = {
    "wind_speed_entity_id": ("_wind_speed",),
    "wind_gust_entity_id": ("_wind_gust", "_max_daily_gust"),
    "precipitation_entity_id": ("_rain_rate_piezo", "_rain_rate", "_precipitation_rate"),
    "dew_point_entity_id": ("_dewpoint", "_dew_point"),
    "visibility_entity_id": ("_visibility",),
    "outdoor_temp_entity_id": ("_outdoor_temperature", "_temperature"),
    "humidity_entity_id": ("_humidity",),
    "solar_radiation_entity_id": ("_solar_radiation",),
}

_STATION_HINTS = ("gw2000", "gw1000", "gw1100", "gw2000a", "ecowitt", "wh90", "ws90", "ws80")


def _available(state: Any) -> bool:
    return bool(state) and state.state not in ("unknown", "unavailable", "")


def _is_indoor(entity_id: str, friendly: str) -> bool:
    blob = f"{entity_id} {friendly}".lower()
    return "indoor" in blob or "inside" in blob


def _station_boost(entity_id: str) -> int:
    low = entity_id.lower()
    return 50 if any(h in low for h in _STATION_HINTS) else 0


def _score_candidate(role: str, entity_id: str, state: Any) -> int:
    friendly = str(state.attributes.get("friendly_name") or "")
    low_id = entity_id.lower()
    low_name = friendly.lower()
    blob = f"{low_id} {low_name}"
    score = _station_boost(entity_id)

    if role == "wind_speed_entity_id":
        if "gust" in blob:
            return -1
        if low_id.endswith("_wind_speed") or low_id.endswith(".wind_speed"):
            score += 100
        elif "wind_speed" in blob or "wind speed" in low_name:
            score += 60
        elif str(state.attributes.get("device_class") or "") == "wind_speed":
            score += 40
        else:
            return -1
        return score

    if role == "wind_gust_entity_id":
        if "max_daily_gust" in low_id:
            score += 70
        elif "wind_gust" in blob or "gust" in low_name:
            score += 100
        else:
            return -1
        return score

    if role == "precipitation_entity_id":
        # Prefer instantaneous rate, never daily/weekly/monthly totals.
        if any(x in blob for x in ("daily", "weekly", "monthly", "yearly", "event_rain", "total")):
            if "rate" not in blob:
                return -1
        if "rain_rate" in low_id or "precipitation_rate" in low_id:
            score += 100
        elif "rain rate" in low_name or "precip rate" in low_name:
            score += 80
        elif "piezo" in blob and "rain" in blob and "rate" in blob:
            score += 90
        else:
            return -1
        return score

    if role == "dew_point_entity_id":
        if _is_indoor(entity_id, friendly):
            return -1
        if "dewpoint" in low_id or "dew_point" in low_id or "dew point" in low_name:
            score += 100
        else:
            return -1
        return score

    if role == "visibility_entity_id":
        if "visibility" in blob:
            score += 100
            return score
        return -1

    if role == "outdoor_temp_entity_id":
        if _is_indoor(entity_id, friendly):
            return -1
        if "outdoor_temperature" in low_id:
            score += 100
        elif "outdoor" in blob and "temp" in blob:
            score += 80
        elif str(state.attributes.get("device_class") or "") == "temperature" and _station_boost(
            entity_id
        ):
            score += 50
        else:
            return -1
        return score

    if role == "humidity_entity_id":
        if _is_indoor(entity_id, friendly):
            return -1
        if low_id.endswith("_humidity") and "indoor" not in low_id:
            score += 100
        elif "humidity" in blob and "indoor" not in blob:
            score += 60
        else:
            return -1
        return score

    if role == "solar_radiation_entity_id":
        if "solar_radiation" in low_id or "solar radiation" in low_name:
            score += 100
        elif "irradiance" in blob:
            score += 70
        else:
            return -1
        return score

    return -1


def detect_local_weather_entities(hass: Any) -> dict[str, str | None]:
    """Return best-guess entity IDs for local weather station roles."""
    best: dict[str, tuple[int, str]] = {}
    for state in hass.states.async_all("sensor"):
        if not _available(state):
            continue
        entity_id = state.entity_id
        for role in WEATHER_SENSOR_ROLES:
            score = _score_candidate(role, entity_id, state)
            if score < 0:
                continue
            prev = best.get(role)
            if prev is None or score > prev[0]:
                best[role] = (score, entity_id)

    return {role: (best[role][1] if role in best else None) for role in WEATHER_SENSOR_ROLES}


def detection_summary(detected: dict[str, str | None]) -> dict[str, Any]:
    mapped = {k: v for k, v in detected.items() if v}
    station = None
    for eid in mapped.values():
        low = eid.lower()
        for hint in _STATION_HINTS:
            if hint in low:
                # Prefer gw2000a-style prefix
                if "_" in eid:
                    station = eid.split(".", 1)[-1].rsplit("_", 1)[0]
                else:
                    station = hint
                break
        if station:
            break
    return {
        "detected": detected,
        "mapped_count": len(mapped),
        "station_hint": station,
        "labels": ROLE_LABELS,
    }
