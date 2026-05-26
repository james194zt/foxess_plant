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
