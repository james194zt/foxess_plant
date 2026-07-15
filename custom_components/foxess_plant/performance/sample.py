"""Collect a performance sample from coordinator state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..smart_charge.battery_metrics import parse_state_float


@dataclass(frozen=True)
class PerformanceSample:
    pv_power_kw: float | None
    net_grid_power_kw: float | None
    load_power_kw: float | None
    string_voltage_v: float | None
    virtual_panel_temp_c: float | None
    wind_speed_ms: float | None
    visibility_km: float | None
    dew_point_c: float | None
    precipitation_mm: float | None
    solcast_forecast_kw: float | None
    clipping_loss_kw: float
    import_p_per_kwh: float | None
    export_p_per_kwh: float | None
    pv_kwh_today: float | None
    solcast_forecast_kwh_today: float | None


def _entity_power_kw(coordinator: Any, key: str) -> float | None:
    from ..discovery import resolve_entity_id

    entity_id = resolve_entity_id(
        coordinator.hass,
        coordinator.plant.entity_map,
        key,
        device_id=coordinator.plant.device_id,
    )
    if not entity_id:
        return None
    state = coordinator.hass.states.get(entity_id)
    if not state or state.state in ("unknown", "unavailable", ""):
        return None
    value = parse_state_float(state.state)
    if value is None:
        return None
    unit = str(state.attributes.get("unit_of_measurement") or "").lower()
    if unit in ("w", "watt", "watts") or abs(value) > 50:
        return abs(value) / 1000.0
    return abs(value)


def _octopus_rates_p_per_kwh(coordinator: Any) -> tuple[float | None, float | None]:
    cache = coordinator._octopus_cache or {}
    imp = cache.get("current_import_p_per_kwh")
    exp = cache.get("current_export_p_per_kwh")
    return (
        float(imp) if imp is not None else None,
        float(exp) if exp is not None else None,
    )


def _ambient_temp_c(hass: Any, coordinator: Any) -> float | None:
    """Prefer mapped outdoor weather sensor; fall back to weather.* temperature."""
    from ..smart_charge.battery_metrics import parse_state_float
    from .weather import (
        _read_entity_state,
        _normalize_entity_id,
        resolve_performance_weather_entity_id,
    )

    outdoor_id = _normalize_entity_id(
        getattr(coordinator.plant.performance, "outdoor_temp_entity_id", None)
    )
    if outdoor_id:
        value, unit = _read_entity_state(hass, outdoor_id)
        if value is not None:
            token = str(unit or "").strip().lower().replace(" ", "")
            if token in ("f", "°f", "fahrenheit"):
                value = (value - 32.0) * 5.0 / 9.0
            return round(value, 1)

    weather_id = resolve_performance_weather_entity_id(coordinator)
    if not weather_id:
        return None
    state = hass.states.get(weather_id)
    if not state:
        return None
    temp = parse_state_float(state.attributes.get("temperature"))
    return float(temp) if temp is not None else None


def collect_performance_sample(coordinator: Any) -> PerformanceSample:
    from .clipping import compute_clipping_loss_kw
    from .virtual_panel_temp import compute_virtual_panel_temp_c
    from .weather import read_weather_metrics

    cfg = coordinator.plant.performance
    pv_kw = _entity_power_kw(coordinator, "pv_power")
    if pv_kw is None:
        for key in ("pv1_power", "pv_power_total"):
            pv_kw = _entity_power_kw(coordinator, key)
            if pv_kw is not None:
                break

    import_kw = None
    export_kw = None
    glow = coordinator._glow_live or {}
    if glow.get("import_kw") is not None:
        import_kw = abs(float(glow["import_kw"]))
    if import_kw is None:
        import_kw = _entity_power_kw(coordinator, "grid_import")
    export_kw = _entity_power_kw(coordinator, "grid_export")

    net_grid = None
    if import_kw is not None or export_kw is not None:
        net_grid = round((export_kw or 0.0) - (import_kw or 0.0), 3)

    load_kw = _entity_power_kw(coordinator, "load_power")

    string_v = coordinator._entity_float("pv1_voltage")
    if string_v is None:
        string_v = coordinator._entity_float("pv1_volts")

    ambient = _ambient_temp_c(coordinator.hass, coordinator)
    virtual_temp = compute_virtual_panel_temp_c(
        string_voltage_v=string_v,
        pv_power_kw=pv_kw,
        baseline_v_at_25c=cfg.baseline_v_at_25c,
        temp_coefficient_v_per_c=cfg.temp_coefficient_v_per_c,
        inverter_ac_limit_kw=cfg.inverter_ac_limit_kw,
        ambient_temp_c=ambient,
    )

    weather = read_weather_metrics(coordinator.hass, coordinator)
    coordinator._last_weather_sources = weather.get("sources")

    solcast_kw = None
    solcast_state = coordinator._solcast_state() if hasattr(coordinator, "_solcast_state") else {}
    power_now_w = solcast_state.get("power_now_w")
    if power_now_w is not None:
        solcast_kw = float(power_now_w) / 1000.0
    elif solcast_state.get("pv_power_now_kw") is not None:
        solcast_kw = float(solcast_state["pv_power_now_kw"])

    recent_peak = float(coordinator._performance_recent_peak_kw or 0.0)
    if pv_kw is not None:
        coordinator._performance_recent_peak_kw = max(recent_peak, pv_kw)

    clipping = compute_clipping_loss_kw(
        pv_power_kw=pv_kw,
        inverter_ac_limit_kw=cfg.inverter_ac_limit_kw,
        recent_peak_kw=coordinator._performance_recent_peak_kw,
    )

    imp_p, exp_p = _octopus_rates_p_per_kwh(coordinator)

    analytics = coordinator._read_analytics() if hasattr(coordinator, "_read_analytics") else {}
    pv_today = analytics.get("pv_production_kwh_today")
    solcast_today = solcast_state.get("forecast_today_kwh")

    return PerformanceSample(
        pv_power_kw=pv_kw,
        net_grid_power_kw=net_grid,
        load_power_kw=load_kw,
        string_voltage_v=string_v,
        virtual_panel_temp_c=virtual_temp,
        wind_speed_ms=weather.get("wind_speed_ms"),
        visibility_km=weather.get("visibility_km"),
        dew_point_c=weather.get("dew_point_c"),
        precipitation_mm=weather.get("precipitation_mm"),
        solcast_forecast_kw=solcast_kw,
        clipping_loss_kw=clipping,
        import_p_per_kwh=imp_p,
        export_p_per_kwh=exp_p,
        pv_kwh_today=float(pv_today) if pv_today is not None else None,
        solcast_forecast_kwh_today=float(solcast_today) if solcast_today is not None else None,
    )
