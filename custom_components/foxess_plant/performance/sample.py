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
    solcast_forecast_kw: float | None
    clipping_loss_kw: float
    import_p_per_kwh: float | None
    export_p_per_kwh: float | None
    pv_kwh_today: float | None
    solcast_forecast_kwh_today: float | None


def _entity_power_kw(coordinator: Any, key: str) -> float | None:
    entity_id = coordinator.plant.entity_map.get(key)
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


def _weather_attrs(coordinator: Any) -> dict[str, Any]:
    entity_id = coordinator.plant.storm_prep.weather_entity_id
    if not entity_id:
        return {}
    state = coordinator.hass.states.get(entity_id)
    if not state:
        return {}
    attrs = dict(state.attributes)
    attrs["state"] = state.state
    return attrs


def _octopus_rates_p_per_kwh(coordinator: Any) -> tuple[float | None, float | None]:
    cache = coordinator._octopus_cache or {}
    imp = cache.get("current_import_p_per_kwh")
    exp = cache.get("current_export_p_per_kwh")
    return (
        float(imp) if imp is not None else None,
        float(exp) if exp is not None else None,
    )


def collect_performance_sample(coordinator: Any) -> PerformanceSample:
    from .clipping import compute_clipping_loss_kw
    from .virtual_panel_temp import compute_virtual_panel_temp_c

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

    virtual_temp = compute_virtual_panel_temp_c(
        string_voltage_v=string_v,
        pv_power_kw=pv_kw,
        baseline_v_at_25c=cfg.baseline_v_at_25c,
        temp_coefficient_v_per_c=cfg.temp_coefficient_v_per_c,
    )

    weather = _weather_attrs(coordinator)
    wind = parse_state_float(weather.get("wind_speed"))
    visibility = parse_state_float(weather.get("visibility"))
    dew = parse_state_float(weather.get("dew_point"))

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
        wind_speed_ms=wind,
        visibility_km=visibility,
        dew_point_c=dew,
        solcast_forecast_kw=solcast_kw,
        clipping_loss_kw=clipping,
        import_p_per_kwh=imp_p,
        export_p_per_kwh=exp_p,
        pv_kwh_today=float(pv_today) if pv_today is not None else None,
        solcast_forecast_kwh_today=float(solcast_today) if solcast_today is not None else None,
    )
