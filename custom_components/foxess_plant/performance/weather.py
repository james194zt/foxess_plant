"""Weather entity resolution and metric extraction for performance sampling."""

from __future__ import annotations

from typing import Any

from ..smart_charge.battery_metrics import parse_state_float


def resolve_performance_weather_entity_id(coordinator: Any) -> str | None:
    """Performance override, then StormSafe, then overview auto-discovery."""
    perf_id = getattr(coordinator.plant.performance, "weather_entity_id", None)
    if perf_id:
        return str(perf_id)
    storm_id = coordinator.plant.storm_prep.weather_entity_id
    if storm_id:
        return str(storm_id)
    from ..storm_weather import resolve_overview_weather_entities

    _, entity_id = resolve_overview_weather_entities(coordinator.hass, coordinator.plant.storm_prep)
    return entity_id


def _weather_state(hass: Any, entity_id: str | None) -> dict[str, Any]:
    if not entity_id:
        return {}
    state = hass.states.get(entity_id)
    if not state:
        return {}
    attrs = dict(state.attributes)
    attrs["state"] = state.state
    return attrs


def _parse_precipitation_mm(attrs: dict[str, Any]) -> float | None:
    for key in ("precipitation", "precipitation_intensity", "precipitation_rate"):
        raw = attrs.get(key)
        value = parse_state_float(raw)
        if value is None:
            continue
        unit = str(attrs.get(f"{key}_unit") or attrs.get("precipitation_unit") or "").lower()
        if unit in ("mm/h", "mm/hr", "mm per hour"):
            return round(value * (5.0 / 60.0), 4)
        if unit in ("m", "meter", "meters"):
            return round(value * 1000.0, 4)
        return round(value, 4)
    condition = str(attrs.get("state") or "").lower()
    if any(w in condition for w in ("rain", "drizzle", "shower", "snow", "sleet")):
        return 0.1
    return None


def fallback_wind_speed_ms(hass: Any, *, weather_entity_id: str | None) -> float | None:
    """Use standalone wind sensors when weather.* wind_speed attr is empty."""
    candidates: list[str] = []
    if weather_entity_id:
        base = weather_entity_id.split(".", 1)[-1]
        for suffix in ("wind_speed", "wind_speed_ms", "wind_speed_m_s"):
            candidates.append(f"sensor.{base}_{suffix}")
            candidates.append(f"sensor.{base}_{suffix.replace('_', '')}")

    for entity_id in candidates:
        state = hass.states.get(entity_id)
        if not state or state.state in ("unknown", "unavailable", ""):
            continue
        value = parse_state_float(state.state)
        if value is not None:
            return value

    for state in hass.states.async_all("sensor"):
        dc = str(state.attributes.get("device_class") or "")
        if dc != "wind_speed":
            continue
        value = parse_state_float(state.state)
        if value is not None:
            return value
    return None


def read_weather_metrics(hass: Any, coordinator: Any) -> dict[str, float | None]:
    """Read wind, visibility, dew point, and bucket precipitation from weather entity."""
    entity_id = resolve_performance_weather_entity_id(coordinator)
    attrs = _weather_state(hass, entity_id)

    wind = parse_state_float(attrs.get("wind_speed"))
    if wind is None:
        wind = fallback_wind_speed_ms(hass, weather_entity_id=entity_id)

    visibility = parse_state_float(attrs.get("visibility"))
    dew = parse_state_float(attrs.get("dew_point"))
    precip = _parse_precipitation_mm(attrs)

    return {
        "weather_entity_id": entity_id,
        "wind_speed_ms": wind,
        "visibility_km": visibility,
        "dew_point_c": dew,
        "precipitation_mm": precip,
    }
