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
    """Current import / export p/kWh: the supplier cache, else the rate rows SmartCharge plans with.

    The cache only exists with an import supplier; export from a sensor or another supplier, and band rates,
    come from the planner's rows (tariff_export.py).
    """
    cache = coordinator._octopus_cache or {}
    imp = cache.get("current_import_p_per_kwh")
    exp = cache.get("current_export_p_per_kwh")
    if (imp is None or exp is None) and hasattr(coordinator, "_smart_charge_rate_rows"):
        from homeassistant.util import dt as dt_util

        from ..octopus_tariff import rate_at

        try:
            import_rows, export_rows = coordinator._smart_charge_rate_rows()
        except Exception:  # noqa: BLE001 — no rates is the old behaviour
            import_rows, export_rows = [], []
        now = dt_util.utcnow()
        if imp is None and import_rows:
            imp = rate_at(now, import_rows)
        if exp is None and export_rows:
            exp = rate_at(now, export_rows)
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


def _string_voltage_v(coordinator: Any) -> float | None:
    """Average live string voltages (ignore dead/idle strings)."""
    from ..discovery import resolve_entity_id
    from ..smart_charge.battery_metrics import parse_state_float

    vals: list[float] = []
    keys = (
        "pv1_voltage",
        "pv2_voltage",
        "pv3_voltage",
        "pv4_voltage",
        "pv1_volts",
        "pv2_volts",
    )
    for key in keys:
        entity_id = resolve_entity_id(
            coordinator.hass,
            coordinator.plant.entity_map,
            key,
            device_id=coordinator.plant.device_id,
        )
        if not entity_id:
            # Fall back to mapped float helper for aliases already in the entity map.
            value = coordinator._entity_float(key)
            if value is not None and float(value) > 50.0:
                vals.append(float(value))
            continue
        state = coordinator.hass.states.get(entity_id)
        if not state or state.state in ("unknown", "unavailable", ""):
            continue
        value = parse_state_float(state.state)
        if value is not None and float(value) > 50.0:
            vals.append(float(value))
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


MIN_PV_KW_FOR_TEMP = 0.05  # below this there's too little sun to say anything about panel heating


def effective_ac_limit_kw(coordinator: Any) -> float:
    """The most the inverter puts out on the AC side.

    The inverter's own installer setting (Max Active Power) when foxess_modbus exposes it, e.g. 3.68 kW on a
    5 kW EVO limited for its grid connection; otherwise the setting, unless it's still the old 4.3 kW default
    and the model name gives the rating.
    """
    from ..inverter_schedule import evo_rated_power_w

    max_kw = coordinator._entity_float("max_active_power") if hasattr(coordinator, "_entity_float") else None
    if max_kw is not None and max_kw > 0:
        return float(max_kw)
    configured = float(coordinator.plant.performance.inverter_ac_limit_kw or 0)
    if configured and abs(configured - 4.3) > 1e-6:
        return configured
    rated = evo_rated_power_w(coordinator._entity_state("pcs_model_name")) if hasattr(coordinator, "_entity_state") else None
    return rated / 1000.0 if rated else (configured or 4.3)


def _model_panel_temp(
    coordinator: Any,
    *,
    pv_kw: float | None,
    ambient: float | None,
    wind_ms: float | None,
    solcast_kw: float | None,
    held_back: bool,
) -> tuple[float | None, float | None]:
    """(panel temperature, the same in still air) from the datasheet model (panel_temp.py)."""
    from .panel_temp import ArrayThermal, plant_panel_temp_c, still_air_temp_c

    if ambient is None or pv_kw is None or pv_kw < MIN_PV_KW_FOR_TEMP:
        return None, None
    pv_config = coordinator.plant.pv_config
    strings = [(cfg, key) for cfg, key in ((pv_config.pv1, "pv1_power"), (pv_config.pv2, "pv2_power")) if cfg.enabled]
    if not strings:
        return None, None
    measured = [_entity_power_kw(coordinator, key) for _, key in strings]
    total_stc = sum(cfg.effective_dc_w for cfg, _ in strings) or 1.0
    if any(power is None for power in measured):
        # No per-string reading: share the total by array size
        measured = [pv_kw * cfg.effective_dc_w / total_stc for cfg, _ in strings]

    # When output is held back (battery full with nowhere to send it, or clipped at the AC limit) the panels
    # still get the full sun: use Solcast's estimate of what they could make instead
    soc = coordinator._entity_float("battery_soc") if hasattr(coordinator, "_entity_float") else None
    limited = held_back or (soc is not None and soc >= 98.0)
    if limited and solcast_kw and solcast_kw > pv_kw > 0:
        measured = [power * solcast_kw / pv_kw for power in measured]

    arrays = [
        (
            ArrayThermal(
                stc_kw=cfg.effective_dc_w / 1000.0,
                noct_c=cfg.noct_c,
                power_temp_coeff_pct=cfg.power_temp_coeff_pct,
                mounting=cfg.mounting,
            ),
            float(power or 0.0),
        )
        for (cfg, _), power in zip(strings, measured)
    ]
    return (
        plant_panel_temp_c(arrays, air_c=ambient, wind_ms=wind_ms),
        still_air_temp_c(arrays, air_c=ambient),
    )


def _thermal_arrays(coordinator: Any) -> list[Any]:
    from .panel_temp import ArrayThermal

    pv_config = coordinator.plant.pv_config
    return [
        ArrayThermal(
            stc_kw=cfg.effective_dc_w / 1000.0,
            noct_c=cfg.noct_c,
            power_temp_coeff_pct=cfg.power_temp_coeff_pct,
            mounting=cfg.mounting,
        )
        for cfg in (pv_config.pv1, pv_config.pv2)
        if cfg.enabled
    ]


def _pv_power_kw(coordinator: Any) -> float | None:
    pv_kw = _entity_power_kw(coordinator, "pv_power")
    if pv_kw is None:
        for key in ("pv1_power", "pv_power_total"):
            pv_kw = _entity_power_kw(coordinator, key)
            if pv_kw is not None:
                break
    return pv_kw


def _clipping_kw(coordinator: Any, pv_kw: float | None, forecast_kw: float | None) -> float:
    from .clipping import compute_clipping_loss_kw

    return compute_clipping_loss_kw(
        pv_power_kw=pv_kw,
        inverter_ac_limit_kw=effective_ac_limit_kw(coordinator),
        potential_kw=forecast_kw,
        ac_output_kw=_entity_power_kw(coordinator, "inv_power"),
        battery_charge_kw=_entity_power_kw(coordinator, "battery_charge"),
    )


def _lagged_panel_temp(
    coordinator: Any,
    *,
    pv_kw: float | None,
    ambient: float | None,
    wind_ms: float | None,
    forecast_kw: float | None,
    held_back: bool,
) -> tuple[float | None, float | None]:
    """The steady-state model, passed through the panels' thermal lag (panel_thermal.py)."""
    from homeassistant.util import dt as dt_util

    target, still_target = _model_panel_temp(
        coordinator, pv_kw=pv_kw, ambient=ambient, wind_ms=wind_ms, solcast_kw=forecast_kw, held_back=held_back
    )
    thermal = getattr(coordinator, "_panel_thermal", None)
    if thermal is None:
        return target, still_target
    return thermal.update(
        now=dt_util.utcnow(),
        target_c=target,
        still_air_target_c=still_target,
        air_c=ambient,
        arrays=_thermal_arrays(coordinator),
        wind_ms=wind_ms,
    )


def step_panel_thermal(coordinator: Any) -> None:
    """The 30-second step between samples, so the lag follows each cloud rather than a 5-minute snapshot."""
    from .weather import read_weather_metrics

    pv_kw = _pv_power_kw(coordinator)
    ambient = _ambient_temp_c(coordinator.hass, coordinator)
    wind_ms = read_weather_metrics(coordinator.hass, coordinator).get("wind_speed_ms")
    forecast_kw = coordinator.pv_forecast_now()[0] if hasattr(coordinator, "pv_forecast_now") else None
    _, still_air = _lagged_panel_temp(
        coordinator,
        pv_kw=pv_kw,
        ambient=ambient,
        wind_ms=wind_ms,
        forecast_kw=forecast_kw,
        held_back=_clipping_kw(coordinator, pv_kw, forecast_kw) > 0,
    )
    coordinator._panel_temp_still_air_c = still_air


def _grid_power_kw(coordinator: Any) -> tuple[float | None, float | None]:
    """Grid import/export kW: inverter CT, or the Glow meter per direction when its option is on."""
    from ..glow_grid import glow_net_power_kw, pick_grid_power_kw

    glow_cfg = coordinator.plant.glow
    import_kw, export_kw, _sources = pick_grid_power_kw(
        ct_import_kw=_entity_power_kw(coordinator, "grid_import"),
        ct_export_kw=_entity_power_kw(coordinator, "grid_export"),
        glow_net_kw=glow_net_power_kw(coordinator._glow_live) if glow_cfg.enabled else None,
        import_from_glow=glow_cfg.grid_import_from_glow,
        export_from_glow=glow_cfg.grid_export_from_glow,
    )
    return import_kw, export_kw


def collect_performance_sample(coordinator: Any) -> PerformanceSample:
    from .weather import read_weather_metrics

    pv_kw = _pv_power_kw(coordinator)

    import_kw, export_kw = _grid_power_kw(coordinator)

    net_grid = None
    if import_kw is not None or export_kw is not None:
        net_grid = round((export_kw or 0.0) - (import_kw or 0.0), 3)

    load_kw = _entity_power_kw(coordinator, "load_power")

    string_v = _string_voltage_v(coordinator)
    ambient = _ambient_temp_c(coordinator.hass, coordinator)

    weather = read_weather_metrics(coordinator.hass, coordinator)
    coordinator._last_weather_sources = weather.get("sources")

    # PV forecast for now and today: Solcast while it's updating, else Open-Meteo (see pv_forecast_now)
    solcast_kw = None
    solcast_today = None
    if hasattr(coordinator, "pv_forecast_now"):
        solcast_kw, solcast_today = coordinator.pv_forecast_now()

    clipping = _clipping_kw(coordinator, pv_kw, solcast_kw)
    virtual_temp, still_air_temp = _lagged_panel_temp(
        coordinator,
        pv_kw=pv_kw,
        ambient=ambient,
        wind_ms=weather.get("wind_speed_ms"),
        forecast_kw=solcast_kw,
        held_back=clipping > 0,
    )
    coordinator._panel_temp_still_air_c = still_air_temp

    imp_p, exp_p = _octopus_rates_p_per_kwh(coordinator)

    analytics = coordinator._read_analytics() if hasattr(coordinator, "_read_analytics") else {}
    pv_today = analytics.get("pv_production_kwh_today")

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
