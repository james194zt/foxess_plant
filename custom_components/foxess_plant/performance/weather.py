"""Weather entity resolution and metric extraction for performance sampling."""

from __future__ import annotations

from typing import Any

from ..smart_charge.battery_metrics import parse_state_float


def _normalize_entity_id(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def resolve_performance_weather_entity_id(coordinator: Any) -> str | None:
    """Performance override, then StormSafe, then overview auto-discovery."""
    perf_id = _normalize_entity_id(getattr(coordinator.plant.performance, "weather_entity_id", None))
    if perf_id:
        return perf_id
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


def _unit_token(unit: str | None) -> str:
    return (
        str(unit or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("⁄", "/")
        .replace("·", "")
    )


def _read_entity_state(hass: Any, entity_id: str | None) -> tuple[float | None, str | None]:
    entity_id = _normalize_entity_id(entity_id)
    if not entity_id:
        return None, None
    state = hass.states.get(entity_id)
    if not state or state.state in ("unknown", "unavailable", ""):
        return None, None
    value = parse_state_float(state.state)
    if value is None:
        return None, None
    unit = _unit_token(state.attributes.get("unit_of_measurement"))
    return float(value), unit or None


def _to_wind_speed_ms(value: float, unit: str | None) -> float:
    token = _unit_token(unit)
    if token in ("m/s", "mps", "meter/s", "meterspersecond", "ms", "mpersec", "metrespersecond"):
        return value
    if token in ("km/h", "kmh", "kph", "kmph", "kilometersperhour", "kilometresperhour"):
        return value / 3.6
    if token in ("mph", "mi/h", "milesperhour", "mile/h"):
        return value * 0.44704
    if token in ("kn", "kt", "knot", "knots"):
        return value * 0.514444
    if token in ("ft/s", "fps"):
        return value * 0.3048
    # Wunderground scraper and many PWS integrations use mph without device_class.
    if value > 35 and token in ("", None):
        return value * 0.44704
    return value


def _to_visibility_km(value: float, unit: str | None) -> float:
    token = _unit_token(unit)
    if token in ("km", "kilometer", "kilometers"):
        return value
    if token in ("m", "meter", "meters"):
        return value / 1000.0
    if token in ("mi", "mile", "miles"):
        return value * 1.60934
    if value > 50 and token in ("", None):
        return value / 1000.0
    return value


def _to_dew_point_c(value: float, unit: str | None) -> float:
    token = _unit_token(unit)
    if token in ("f", "°f", "fahrenheit"):
        return (value - 32.0) * 5.0 / 9.0
    return value


def _rate_to_bucket_mm(value: float, unit: str | None) -> float:
    """Convert precipitation rate to mm fallen in a 5-minute bucket."""
    token = _unit_token(unit)
    mm_per_hour: float
    if token in ("mm/h", "mm/hr", "mmh", "mmperhour"):
        mm_per_hour = value
    elif token in ("in/h", "in/hr", "inh", "inperhour", "in/hour"):
        mm_per_hour = value * 25.4
    elif token in ("mm", "millimeter", "millimeters"):
        return round(value, 4)
    elif token in ("in", "inch", "inches"):
        return round(value * 25.4, 4)
    elif token in ("mm/s",):
        mm_per_hour = value * 3600.0
    else:
        mm_per_hour = value * 25.4 if value <= 2.0 else value
    return round(max(0.0, mm_per_hour) * (5.0 / 60.0), 4)


def _parse_precipitation_mm_from_attrs(attrs: dict[str, Any]) -> float | None:
    for key in ("precipitation", "precipitation_intensity", "precipitation_rate"):
        raw = attrs.get(key)
        value = parse_state_float(raw)
        if value is None:
            continue
        unit = str(attrs.get(f"{key}_unit") or attrs.get("precipitation_unit") or "").lower()
        if unit in ("mm/h", "mm/hr", "mm per hour"):
            return round(value * (5.0 / 60.0), 4)
        if unit in ("in/h", "in/hr", "in per hour"):
            return round(value * 25.4 * (5.0 / 60.0), 4)
        if unit in ("m", "meter", "meters"):
            return round(value * 1000.0, 4)
        if unit in ("mm",):
            return round(value, 4)
        if unit in ("in", "inch", "inches"):
            return round(value * 25.4, 4)
        return _rate_to_bucket_mm(value, unit)
    condition = str(attrs.get("state") or "").lower()
    if any(w in condition for w in ("rain", "drizzle", "shower", "snow", "sleet")):
        return 0.1
    return None


def _metric_from_entity(
    hass: Any,
    entity_id: str | None,
    *,
    kind: str,
) -> float | None:
    value, unit = _read_entity_state(hass, entity_id)
    if value is None:
        return None
    if kind == "wind_speed_ms":
        return round(_to_wind_speed_ms(value, unit), 3)
    if kind == "visibility_km":
        return round(_to_visibility_km(value, unit), 2)
    if kind == "dew_point_c":
        return round(_to_dew_point_c(value, unit), 1)
    if kind == "precipitation_mm":
        return _rate_to_bucket_mm(value, unit)
    return None


def _heuristic_wind_entity(hass: Any, *, weather_entity_id: str | None) -> str | None:
    candidates: list[str] = []
    if weather_entity_id:
        base = weather_entity_id.split(".", 1)[-1]
        for suffix in ("wind_speed", "wind_speed_ms", "wind_speed_m_s"):
            candidates.append(f"sensor.{base}_{suffix}")
            candidates.append(f"sensor.{base}_{suffix.replace('_', '')}")

    for entity_id in candidates:
        value, _ = _read_entity_state(hass, entity_id)
        if value is not None:
            return entity_id

    for state in hass.states.async_all("sensor"):
        if str(state.attributes.get("device_class") or "") != "wind_speed":
            continue
        if parse_state_float(state.state) is not None:
            return state.entity_id
    return None


def read_weather_metrics(hass: Any, coordinator: Any) -> dict[str, float | None]:
    """Read wind, visibility, dew point, and bucket precipitation for performance sampling."""
    cfg = coordinator.plant.performance
    weather_entity_id = resolve_performance_weather_entity_id(coordinator)
    attrs = _weather_state(hass, weather_entity_id)

    sources: dict[str, str | None] = {}

    wind_entity = _normalize_entity_id(getattr(cfg, "wind_speed_entity_id", None))
    if wind_entity:
        wind = _metric_from_entity(hass, wind_entity, kind="wind_speed_ms")
        sources["wind_speed_ms"] = wind_entity if wind is not None else None
    else:
        wind = parse_state_float(attrs.get("wind_speed"))
        if wind is not None:
            wind = _to_wind_speed_ms(float(wind), "m/s")
            sources["wind_speed_ms"] = weather_entity_id
        else:
            fallback_id = _heuristic_wind_entity(hass, weather_entity_id=weather_entity_id)
            wind = _metric_from_entity(hass, fallback_id, kind="wind_speed_ms") if fallback_id else None
            sources["wind_speed_ms"] = fallback_id if wind is not None else None

    vis_entity = _normalize_entity_id(getattr(cfg, "visibility_entity_id", None))
    if vis_entity:
        visibility = _metric_from_entity(hass, vis_entity, kind="visibility_km")
        sources["visibility_km"] = vis_entity if visibility is not None else None
    else:
        visibility = parse_state_float(attrs.get("visibility"))
        if visibility is not None:
            visibility = _to_visibility_km(float(visibility), "km")
            sources["visibility_km"] = weather_entity_id
        else:
            visibility = None
            sources["visibility_km"] = None

    dew_entity = _normalize_entity_id(getattr(cfg, "dew_point_entity_id", None))
    if dew_entity:
        dew = _metric_from_entity(hass, dew_entity, kind="dew_point_c")
        sources["dew_point_c"] = dew_entity if dew is not None else None
    else:
        dew = parse_state_float(attrs.get("dew_point"))
        if dew is not None:
            dew = _to_dew_point_c(float(dew), "°C")
            sources["dew_point_c"] = weather_entity_id
        else:
            dew = None
            sources["dew_point_c"] = None

    precip_entity = _normalize_entity_id(getattr(cfg, "precipitation_entity_id", None))
    if precip_entity:
        precip = _metric_from_entity(hass, precip_entity, kind="precipitation_mm")
        sources["precipitation_mm"] = precip_entity if precip is not None else None
    else:
        precip = _parse_precipitation_mm_from_attrs(attrs)
        sources["precipitation_mm"] = weather_entity_id if precip is not None else None

    return {
        "weather_entity_id": weather_entity_id,
        "wind_speed_ms": wind,
        "visibility_km": visibility,
        "dew_point_c": dew,
        "precipitation_mm": precip,
        "sources": sources,
    }
