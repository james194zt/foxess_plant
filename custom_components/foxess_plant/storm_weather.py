"""Google Weather condition evaluation for StormSafe."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, State

# Google Weather API weatherCondition.type values that arm StormSafe.
# Source: ha_google_weather weather.py CONDITION_MAP + Google Weather API enum.
DEFAULT_STORM_GOOGLE_WEATHER_TYPES: frozenset[str] = frozenset(
    {
        "WINDY",
        "WIND_AND_RAIN",
        "HEAVY_RAIN",
        "HEAVY_RAIN_SHOWERS",
        "MODERATE_TO_HEAVY_RAIN",
        "RAIN_PERIODICALLY_HEAVY",
        "HAIL",
        "HAIL_SHOWERS",
        "THUNDERSTORM",
        "THUNDERSHOWER",
        "LIGHT_THUNDERSTORM_RAIN",
        "SCATTERED_THUNDERSTORMS",
        "HEAVY_THUNDERSTORM",
        "SEVERE_THUNDERSTORM",
        "TORNADO",
        "HURRICANE",
        "TROPICAL_STORM",
        "SNOWSTORM",
        "HEAVY_SNOW_STORM",
        "BLIZZARD",
        "BLOWING_SNOW",
        "HEAVY_SNOW",
        "SNOW_PERIODICALLY_HEAVY",
        "MODERATE_TO_HEAVY_SNOW",
        "HEAVY_SNOW_SHOWERS",
    }
)

# Home Assistant weather entity states (mapped from Google types in ha_google_weather).
DEFAULT_STORM_HA_WEATHER_CONDITIONS: frozenset[str] = frozenset(
    {
        "lightning",
        "lightning-rainy",
        "pouring",
        "hail",
        "exceptional",
        "snowy",
        "snowy-rainy",
        "windy",
        "windy-variant",
    }
)

STORM_GOOGLE_TYPE_LABELS: dict[str, str] = {
    "WINDY": "Windy",
    "WIND_AND_RAIN": "Wind and rain",
    "HEAVY_RAIN": "Heavy rain",
    "HEAVY_RAIN_SHOWERS": "Heavy rain showers",
    "MODERATE_TO_HEAVY_RAIN": "Moderate to heavy rain",
    "RAIN_PERIODICALLY_HEAVY": "Periodically heavy rain",
    "HAIL": "Hail",
    "HAIL_SHOWERS": "Hail showers",
    "THUNDERSTORM": "Thunderstorm",
    "THUNDERSHOWER": "Thunder shower",
    "LIGHT_THUNDERSTORM_RAIN": "Light thunderstorm rain",
    "SCATTERED_THUNDERSTORMS": "Scattered thunderstorms",
    "HEAVY_THUNDERSTORM": "Heavy thunderstorm",
    "SEVERE_THUNDERSTORM": "Severe thunderstorm",
    "TORNADO": "Tornado",
    "HURRICANE": "Hurricane",
    "TROPICAL_STORM": "Tropical storm",
    "SNOWSTORM": "Snowstorm",
    "HEAVY_SNOW_STORM": "Heavy snow storm",
    "BLIZZARD": "Blizzard",
    "BLOWING_SNOW": "Blowing snow",
    "HEAVY_SNOW": "Heavy snow",
    "SNOW_PERIODICALLY_HEAVY": "Periodically heavy snow",
    "MODERATE_TO_HEAVY_SNOW": "Moderate to heavy snow",
    "HEAVY_SNOW_SHOWERS": "Heavy snow showers",
}


def storm_google_types(storm_types: list[str] | None) -> frozenset[str]:
    if not storm_types:
        return DEFAULT_STORM_GOOGLE_WEATHER_TYPES
    return frozenset(storm_types)


def is_storm_google_type(
    condition_type: str | None,
    *,
    storm_types: frozenset[str] | None = None,
) -> bool:
    if not condition_type:
        return False
    allowed = storm_types or DEFAULT_STORM_GOOGLE_WEATHER_TYPES
    return condition_type.upper() in allowed


def is_storm_ha_condition(condition: str | None) -> bool:
    if not condition:
        return False
    return condition.lower() in DEFAULT_STORM_HA_WEATHER_CONDITIONS


def read_condition_snapshot(
    hass: HomeAssistant,
    condition_entity_id: str | None,
    weather_entity_id: str | None,
    *,
    storm_types: list[str] | None = None,
) -> dict[str, Any] | None:
    """Current Google type / HA condition and whether StormSafe would arm."""
    allowed = storm_google_types(storm_types)

    if condition_entity_id:
        state = hass.states.get(condition_entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            google_type = state.attributes.get("type")
            if isinstance(google_type, str):
                google_type = google_type.upper()
            active = is_storm_google_type(google_type, storm_types=allowed)
            return {
                "source": "google_type",
                "entity_id": condition_entity_id,
                "text": state.state,
                "type": google_type,
                "is_storm": active,
                "label": STORM_GOOGLE_TYPE_LABELS.get(google_type or "", google_type or state.state),
            }

    if weather_entity_id:
        state = hass.states.get(weather_entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            ha_cond = state.state.lower()
            active = is_storm_ha_condition(ha_cond)
            return {
                "source": "ha_condition",
                "entity_id": weather_entity_id,
                "text": state.state,
                "type": ha_cond,
                "is_storm": active,
                "label": ha_cond.replace("-", " ").title(),
            }

    return None


def is_storm_weather_active(
    hass: HomeAssistant,
    *,
    condition_entity_id: str | None,
    weather_entity_id: str | None,
    use_weather_condition: bool,
    storm_types: list[str] | None = None,
) -> bool:
    if not use_weather_condition:
        return False
    snap = read_condition_snapshot(
        hass,
        condition_entity_id,
        weather_entity_id,
        storm_types=storm_types,
    )
    return bool(snap and snap.get("is_storm"))


def storm_type_catalog() -> list[dict[str, str]]:
    """Human-readable list of Google types that arm StormSafe (for the panel)."""
    return [
        {"type": key, "label": STORM_GOOGLE_TYPE_LABELS[key]}
        for key in sorted(DEFAULT_STORM_GOOGLE_WEATHER_TYPES)
    ]


def _weather_icon_key(condition_type: str | None, *, source: str) -> str:
    if not condition_type:
        return "unknown"
    if source == "google_type":
        token = condition_type.upper()
        if any(k in token for k in ("THUNDER", "TORNADO", "HURRICANE", "TROPICAL")):
            return "storm"
        if any(k in token for k in ("RAIN", "DRIZZLE", "SHOWER")):
            return "rain"
        if any(k in token for k in ("SNOW", "BLIZZARD", "SLEET", "ICE")):
            return "snow"
        if any(k in token for k in ("FOG", "MIST", "HAZE", "SMOG")):
            return "fog"
        if any(k in token for k in ("WIND", "GALE", "BREEZE")):
            return "wind"
        if "PARTLY" in token or "INTERMITTENT" in token:
            return "partly-cloudy"
        if any(k in token for k in ("CLOUD", "OVERCAST")):
            return "cloudy"
        if any(k in token for k in ("CLEAR", "SUNNY", "FAIR")):
            return "sunny"
        return "unknown"
    token = condition_type.lower()
    if token in {"lightning", "lightning-rainy", "exceptional"}:
        return "storm"
    if token in {"rainy", "pouring"}:
        return "rain"
    if token in {"snowy", "snowy-rainy"}:
        return "snow"
    if token == "fog":
        return "fog"
    if token in {"windy", "windy-variant", "hail"}:
        return "wind"
    if token == "partlycloudy":
        return "partly-cloudy"
    if token == "cloudy":
        return "cloudy"
    if token == "sunny":
        return "sunny"
    return "unknown"


def _weather_short_label(icon_key: str, snap: dict[str, Any] | None) -> str:
    defaults = {
        "sunny": "Sunny",
        "partly-cloudy": "Partly cloudy",
        "cloudy": "Cloudy",
        "rain": "Rainy",
        "snow": "Snowy",
        "storm": "Stormy",
        "fog": "Foggy",
        "wind": "Windy",
        "unknown": "Weather",
    }
    if snap and snap.get("label"):
        return str(snap["label"])
    return defaults.get(icon_key, "Weather")


def _format_temperature(temp: Any, unit: str | None) -> str | None:
    if temp is None:
        return None
    try:
        value = round(float(temp))
    except (TypeError, ValueError):
        return None
    if unit in (None, "", "°C", "C", "celsius"):
        return f"{value}°C"
    if unit in ("°F", "F", "fahrenheit"):
        return f"{value}°F"
    return f"{value}{unit}"


def resolve_overview_weather_entities(hass: HomeAssistant, storm_prep: Any) -> tuple[str | None, str | None]:
    """Google Weather condition + weather entities for the overview header."""
    from .panel_config import discover_google_weather, resolve_google_weather_entry

    condition_entity_id = getattr(storm_prep, "condition_entity_id", None)
    weather_entity_id = getattr(storm_prep, "weather_entity_id", None)
    if condition_entity_id or weather_entity_id:
        return condition_entity_id, weather_entity_id

    entry_id = getattr(storm_prep, "google_weather_entry_id", None)
    if entry_id:
        resolved = resolve_google_weather_entry(hass, entry_id)
        return resolved.get("condition_entity_id"), resolved.get("weather_entity_id")

    entries = discover_google_weather(hass).get("entries") or []
    if len(entries) == 1:
        entry = entries[0]
        return entry.get("condition_entity_id"), entry.get("weather_entity")
    return None, None


def read_overview_weather(hass: HomeAssistant, storm_prep: Any) -> dict[str, Any] | None:
    """Current temperature + condition for the overview header (Google Weather)."""
    condition_entity_id, weather_entity_id = resolve_overview_weather_entities(hass, storm_prep)
    storm_types = getattr(storm_prep, "storm_google_types", None)
    snap = read_condition_snapshot(
        hass,
        condition_entity_id,
        weather_entity_id,
        storm_types=storm_types,
    )

    temperature: float | None = None
    temperature_unit: str | None = None
    if weather_entity_id:
        weather_state = hass.states.get(weather_entity_id)
        if weather_state and weather_state.state not in ("unknown", "unavailable"):
            attrs = weather_state.attributes
            raw_temp = attrs.get("temperature")
            if raw_temp is not None:
                try:
                    temperature = float(raw_temp)
                except (TypeError, ValueError):
                    temperature = None
            temperature_unit = attrs.get("temperature_unit") or attrs.get("unit_of_measurement")

    if snap is None and temperature is None:
        return None

    source = (snap or {}).get("source") or "ha_condition"
    condition_type = (snap or {}).get("type")
    icon_key = _weather_icon_key(condition_type, source=source)
    return {
        "temperature": temperature,
        "temperature_unit": temperature_unit,
        "temperature_display": _format_temperature(temperature, temperature_unit),
        "condition_label": _weather_short_label(icon_key, snap),
        "condition_type": condition_type,
        "icon_key": icon_key,
        "weather_entity_id": weather_entity_id,
        "condition_entity_id": condition_entity_id,
    }
