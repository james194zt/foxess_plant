"""House-load energy budget from Solcast 24h forecast — not fixed 100% SOC."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .solcast_remaining import solcast_forecast_kwh_for_horizon
from ..solcast_forecast_metrics import compute_forecast_metrics


@dataclass(frozen=True)
class HouseEnergyBudget:
    dark_hours_kwh: float
    pv_cover_kwh: float
    grid_gap_kwh: float
    target_kwh: float
    target_soc_pct: float
    forecast_horizon_kwh: float | None
    forecast_tomorrow_kwh: float | None


def compute_house_energy_budget(
    *,
    forecast_rows: list[dict[str, Any]],
    avg_home_load_kw: float,
    dark_hours_estimate: float,
    solar_safety_margin: float,
    capacity_kwh: float | None,
    max_target_soc: float,
    reserve_kwh: float,
    horizon_hours: float = 24.0,
) -> HouseEnergyBudget:
    load_kw = max(0.0, avg_home_load_kw)
    dark_hours = max(0.0, dark_hours_estimate)
    margin = max(1.0, solar_safety_margin)
    ceiling_soc = min(100.0, max(10.0, max_target_soc))

    dark_hours_kwh = load_kw * dark_hours
    metrics = compute_forecast_metrics(None, forecast_rows) if forecast_rows else {}
    forecast_tomorrow = metrics.get("forecast_tomorrow_kwh")
    forecast_horizon = solcast_forecast_kwh_for_horizon(forecast_rows, horizon_hours=horizon_hours)
    pv_source = forecast_horizon
    if pv_source is None and forecast_tomorrow is not None:
        pv_source = float(forecast_tomorrow)
    pv_cover_kwh = max(0.0, (pv_source or 0.0) / margin)
    grid_gap_kwh = max(0.0, dark_hours_kwh - pv_cover_kwh)
    target_kwh = reserve_kwh + grid_gap_kwh

    if capacity_kwh is not None and capacity_kwh > 0:
        target_soc_pct = min(ceiling_soc, target_kwh / capacity_kwh * 100.0)
        target_soc_pct = max(1.0, target_soc_pct)
    else:
        target_soc_pct = ceiling_soc

    return HouseEnergyBudget(
        dark_hours_kwh=round(dark_hours_kwh, 2),
        pv_cover_kwh=round(pv_cover_kwh, 2),
        grid_gap_kwh=round(grid_gap_kwh, 2),
        target_kwh=round(target_kwh, 2),
        target_soc_pct=round(target_soc_pct, 1),
        forecast_horizon_kwh=round(forecast_horizon, 2) if forecast_horizon is not None else None,
        forecast_tomorrow_kwh=round(float(forecast_tomorrow), 2) if forecast_tomorrow is not None else None,
    )
