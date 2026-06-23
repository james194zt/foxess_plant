"""Shared SmartCharge evaluation context."""

from __future__ import annotations

from typing import Any

from .reserve import OPERATING_MODE_MAX_SAFETY, compute_exportable_kwh, compute_outage_reserve_kwh
from .solcast_budget import compute_house_energy_budget


def config_float(config: Any, key: str, default: float) -> float:
    try:
        return float(getattr(config, key, default) or default)
    except (TypeError, ValueError):
        return default


def effective_home_load_kw(config: Any, live_load_kw: float | None) -> float:
    reserve_load = getattr(config, "outage_reserve_load_kw", None)
    if reserve_load is not None:
        try:
            return max(0.0, float(reserve_load))
        except (TypeError, ValueError):
            pass
    if live_load_kw is not None and live_load_kw > 0:
        return live_load_kw
    return config_float(config, "house_load_kw_fallback", 1.0)


def max_target_soc(config: Any) -> float:
    explicit = getattr(config, "max_target_soc", None)
    if explicit is not None:
        return min(100.0, max(10.0, float(explicit)))
    return min(100.0, max(10.0, config_float(config, "target_soc", 100.0)))


def build_context(
    *,
    config: Any,
    soc_pct: float | None,
    capacity_kwh: float | None,
    kwh_remaining: float | None,
    forecast_rows: list[dict[str, Any]],
    live_load_kw: float | None,
    horizon_hours: float,
) -> dict[str, Any]:
    operating_mode = str(getattr(config, "operating_mode", OPERATING_MODE_MAX_SAFETY) or OPERATING_MODE_MAX_SAFETY)
    load_kw = effective_home_load_kw(config, live_load_kw)
    reserve_kwh = compute_outage_reserve_kwh(
        avg_home_load_kw=load_kw,
        vulnerable_hours=config_float(config, "outage_reserve_hours", 3.0),
        safety_margin=config_float(config, "outage_reserve_margin", 1.2),
        operating_mode=operating_mode,
        safety_reserve_multiplier=config_float(config, "safety_reserve_multiplier", 1.5),
    )
    exportable_kwh = compute_exportable_kwh(kwh_remaining=kwh_remaining, reserve_kwh=reserve_kwh)
    budget = compute_house_energy_budget(
        forecast_rows=forecast_rows,
        avg_home_load_kw=load_kw,
        dark_hours_estimate=config_float(config, "dark_hours_estimate", 8.0),
        solar_safety_margin=config_float(config, "solar_safety_margin", 1.15),
        capacity_kwh=capacity_kwh,
        max_target_soc=max_target_soc(config),
        reserve_kwh=reserve_kwh,
        horizon_hours=horizon_hours,
    )
    return {
        "operating_mode": operating_mode,
        "reserve_kwh": round(reserve_kwh, 2),
        "exportable_kwh": round(exportable_kwh, 2) if exportable_kwh is not None else None,
        "target_soc_pct": budget.target_soc_pct,
        "grid_gap_kwh": budget.grid_gap_kwh,
        "dark_hours_kwh": budget.dark_hours_kwh,
        "budget": budget,
    }
