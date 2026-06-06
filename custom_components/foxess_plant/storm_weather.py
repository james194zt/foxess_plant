"""Google Weather condition evaluation for StormSafe."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, State

# Home Assistant weather entity states (mapped from Google types in ha_google_weather).
DEFAULT_STORM_HA_WEATHER_CONDITIONS: frozenset[str] = frozenset(
    {
        "lightning",
        "lightning-rainy",
        "pouring",
        "rainy",
        "hail",
        "exceptional",
        "snowy",
        "snowy-rainy",
        "windy",
        "windy-variant",
        "hurricane",
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
    "TYPHOON": "Typhoon",
    "CYCLONE": "Cyclone",
    "TROPICAL_CYCLONE": "Tropical cyclone",
    "EXTRATROPICAL_CYCLONE": "Extra-tropical cyclone",
    "SNOWSTORM": "Snowstorm",
    "HEAVY_SNOW_STORM": "Heavy snow storm",
    "BLIZZARD": "Blizzard",
    "BLOWING_SNOW": "Blowing snow",
    "HEAVY_SNOW": "Heavy snow",
    "SNOW_PERIODICALLY_HEAVY": "Periodically heavy snow",
    "MODERATE_TO_HEAVY_SNOW": "Moderate to heavy snow",
    "HEAVY_SNOW_SHOWERS": "Heavy snow showers",
    "HEAT": "Extreme heat",
    "COLD": "Extreme cold",
    "WIND_CHILL": "Wind chill",
    "DUST_STORM": "Dust storm",
    "WILDFIRE": "Wildfire",
    "FIRE": "Fire",
    "BUSHFIRE": "Bushfire",
    "FIRE_WEATHER": "Fire weather",
    "ICE_STORM": "Ice storm",
    "WINTER_STORM": "Winter storm",
    "GLAZE": "Glaze ice",
    "FREEZING_RAIN": "Freezing rain",
}

# Fox-app style warning groups mapped to Google Weather condition / alert types.
STORM_WEATHER_CATEGORIES: tuple[dict[str, Any], ...] = (
    {
        "id": "extreme_heat",
        "label": "Extreme heat",
        "icon": "storm_weather_extreme_heat.png",
        "google_types": frozenset({"HEAT"}),
        "ha_conditions": frozenset({"exceptional"}),
    },
    {
        "id": "extreme_cold",
        "label": "Extreme cold",
        "icon": "storm_weather_extreme_cold.png",
        "google_types": frozenset(
            {
                "COLD",
                "WIND_CHILL",
                "BLIZZARD",
                "BLOWING_SNOW",
                "HEAVY_SNOW",
                "HEAVY_SNOW_STORM",
                "SNOWSTORM",
                "HEAVY_SNOW_SHOWERS",
                "MODERATE_TO_HEAVY_SNOW",
                "SNOW_PERIODICALLY_HEAVY",
            }
        ),
        "ha_conditions": frozenset({"snowy", "exceptional"}),
    },
    {
        "id": "heavy_rain",
        "label": "Heavy rain",
        "icon": "storm_weather_heavy_rain.png",
        "google_types": frozenset(
            {
                "HEAVY_RAIN",
                "HEAVY_RAIN_SHOWERS",
                "MODERATE_TO_HEAVY_RAIN",
                "RAIN_PERIODICALLY_HEAVY",
                "WIND_AND_RAIN",
            }
        ),
        "ha_conditions": frozenset({"pouring", "rainy"}),
    },
    {
        "id": "typhoons",
        "label": "Typhoons",
        "icon": "storm_weather_typhoons.png",
        "google_types": frozenset(
            {
                "TYPHOON",
                "HURRICANE",
                "TROPICAL_STORM",
                "CYCLONE",
                "TROPICAL_CYCLONE",
                "EXTRATROPICAL_CYCLONE",
                "WINDY",
            }
        ),
        "ha_conditions": frozenset({"exceptional", "hurricane", "windy"}),
    },
    {
        "id": "dust_storm",
        "label": "Dust storm",
        "icon": "storm_weather_dust_storm.png",
        "google_types": frozenset({"DUST_STORM"}),
        "ha_conditions": frozenset({"windy-variant"}),
    },
    {
        "id": "thunderstorms",
        "label": "Thunderstorms",
        "icon": "storm_weather_thunderstorms.png",
        "google_types": frozenset(
            {
                "THUNDERSTORM",
                "THUNDERSHOWER",
                "LIGHT_THUNDERSTORM_RAIN",
                "SCATTERED_THUNDERSTORMS",
                "HEAVY_THUNDERSTORM",
                "SEVERE_THUNDERSTORM",
                "TORNADO",
            }
        ),
        "ha_conditions": frozenset({"lightning", "lightning-rainy"}),
    },
    {
        "id": "wildfires",
        "label": "Wildfires",
        "icon": "storm_weather_wildfires.png",
        "google_types": frozenset({"WILDFIRE", "FIRE", "BUSHFIRE", "FIRE_WEATHER"}),
        "ha_conditions": frozenset({"exceptional"}),
    },
    {
        "id": "hailstorms",
        "label": "Hailstorms",
        "icon": "storm_weather_hailstorms.png",
        "google_types": frozenset({"HAIL", "HAIL_SHOWERS"}),
        "ha_conditions": frozenset({"hail"}),
    },
    {
        "id": "ice_storms",
        "label": "Ice storms",
        "icon": "storm_weather_ice_storms.png",
        "google_types": frozenset({"ICE_STORM", "WINTER_STORM", "GLAZE", "FREEZING_RAIN"}),
        "ha_conditions": frozenset({"snowy-rainy", "exceptional"}),
    },
)

STORM_WEATHER_CATEGORY_BY_ID = {row["id"]: row for row in STORM_WEATHER_CATEGORIES}

DEFAULT_STORM_GOOGLE_WEATHER_TYPES: frozenset[str] = frozenset(
    {t for row in STORM_WEATHER_CATEGORIES for t in row["google_types"]}
)

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


def default_storm_category_ids() -> list[str]:
    return [row["id"] for row in STORM_WEATHER_CATEGORIES]


def storm_weather_category_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "label": row["label"],
            "icon": row["icon"],
            "google_types": sorted(row["google_types"]),
        }
        for row in STORM_WEATHER_CATEGORIES
    ]


def google_types_from_categories(category_ids: list[str] | None) -> list[str] | None:
    if category_ids is None:
        return None
    merged: set[str] = set()
    for cid in category_ids:
        row = STORM_WEATHER_CATEGORY_BY_ID.get(cid)
        if row:
            merged |= set(row["google_types"])
    return sorted(merged)


def categories_from_google_types(storm_types: list[str] | None) -> list[str]:
    if storm_types is None:
        return default_storm_category_ids()
    allowed = {str(t).upper() for t in storm_types}
    if not allowed:
        return []
    selected: list[str] = []
    for row in STORM_WEATHER_CATEGORIES:
        if row["google_types"] & allowed:
            selected.append(row["id"])
    return selected


def ha_conditions_for_storm_types(storm_types: list[str] | None) -> frozenset[str]:
    allowed = storm_google_types(storm_types)
    merged: set[str] = set()
    for row in STORM_WEATHER_CATEGORIES:
        if row["google_types"] & allowed:
            merged |= set(row["ha_conditions"])
    return frozenset(merged) if merged else DEFAULT_STORM_HA_WEATHER_CONDITIONS


def is_storm_ha_condition_for_types(condition: str | None, storm_types: list[str] | None) -> bool:
    if not condition:
        return False
    token = condition.lower()
    if storm_types is None:
        return is_storm_ha_condition(token)
    return token in ha_conditions_for_storm_types(storm_types)


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
            active = is_storm_ha_condition_for_types(ha_cond, storm_types)
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
    """Flat Google type list (advanced / legacy)."""
    allowed = storm_google_types(None)
    return [
        {"type": key, "label": STORM_GOOGLE_TYPE_LABELS.get(key, key.replace("_", " ").title())}
        for key in sorted(allowed)
    ]


def _weather_icon_key_from_text(text: str | None) -> str | None:
    """Infer icon from localized condition text (Google sensor state)."""
    if not text:
        return None
    normalized = text.strip().lower().replace("-", " ").replace("_", " ")
    if any(
        phrase in normalized
        for phrase in (
            "thunder",
            "tornado",
            "hurricane",
            "tropical storm",
            "severe",
        )
    ):
        return "storm"
    if any(phrase in normalized for phrase in ("rain", "drizzle", "shower", "precipitation")):
        return "rain"
    if any(phrase in normalized for phrase in ("snow", "blizzard", "sleet", "ice", "hail")):
        return "snow"
    if any(phrase in normalized for phrase in ("fog", "mist", "haze", "smog")):
        return "fog"
    if "wind" in normalized or "gale" in normalized or "breeze" in normalized:
        return "wind"
    if "mostly cloudy" in normalized or "overcast" in normalized:
        return "partly-cloudy"
    if "partly" in normalized or "intermittent" in normalized:
        return "partly-cloudy"
    if "cloud" in normalized:
        return "cloudy"
    if any(phrase in normalized for phrase in ("clear", "sunny", "fair")):
        return "sunny"
    return None


def _weather_icon_key(
    condition_type: str | None,
    *,
    source: str,
    text: str | None = None,
) -> str:
    if condition_type:
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
            if "MOSTLY" in token and "CLOUD" in token:
                return "partly-cloudy"
            if "PARTLY" in token or "INTERMITTENT" in token:
                return "partly-cloudy"
            if any(k in token for k in ("CLOUD", "OVERCAST")):
                return "cloudy"
            if any(k in token for k in ("CLEAR", "SUNNY", "FAIR")):
                return "sunny"
        else:
            token = condition_type.lower()
            if token in {"lightning", "lightning-rainy", "exceptional", "hurricane"}:
                return "storm"
            if token in {"rainy", "pouring"}:
                return "rain"
            if token in {"snowy", "snowy-rainy"}:
                return "snow"
            if token == "fog":
                return "fog"
            if token in {"windy", "windy-variant", "hail"}:
                return "wind"
            if token in {"partlycloudy", "partly-cloudy"}:
                return "partly-cloudy"
            if token == "cloudy":
                return "cloudy"
            if token in {"sunny", "clear-night"}:
                return "sunny"

    from_text = _weather_icon_key_from_text(text)
    if from_text:
        return from_text
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
    condition_text = (snap or {}).get("text")
    icon_key = _weather_icon_key(condition_type, source=source, text=condition_text)
    if icon_key == "unknown" and weather_entity_id:
        weather_state = hass.states.get(weather_entity_id)
        if weather_state and weather_state.state not in ("unknown", "unavailable"):
            icon_key = _weather_icon_key(
                weather_state.state,
                source="ha_condition",
                text=condition_text,
            )
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
