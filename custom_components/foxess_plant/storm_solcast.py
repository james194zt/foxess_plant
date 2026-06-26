"""StormSafe + Solcast — limit grid pre-charge when PV forecast covers the deficit."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .models import ChargePeriodConfig
from .smart_charge import battery_deficit_kwh
from .solcast_forecast_metrics import _build_intervals, _overlap_kwh

ACTION_FULL_GRID = "full_grid"
ACTION_PV_ONLY = "pv_only"
ACTION_DISABLED = "disabled"
ACTION_UNAVAILABLE = "unavailable"


def _target_soc_pct(cfg: Any) -> float:
    target = getattr(cfg, "target_max_soc", None)
    if target is not None:
        try:
            return float(target)
        except (TypeError, ValueError):
            pass
    return 100.0


def _hours_until_storm(forecast_detail: dict[str, Any] | None) -> float | None:
    if not forecast_detail:
        return None
    next_storm = forecast_detail.get("next_storm")
    if not isinstance(next_storm, dict):
        return None
    try:
        hours = float(next_storm.get("hours_until"))
    except (TypeError, ValueError):
        return None
    return max(0.0, hours) if hours >= 0 else None


def _pv_kwh_before(
    rows: list[dict[str, Any]],
    *,
    window_end: datetime,
) -> float | None:
    intervals = _build_intervals(rows)
    if not intervals:
        return None
    now = dt_util.now()
    if window_end <= now:
        return 0.0
    total = 0.0
    for interval in intervals:
        total += _overlap_kwh(interval, now, window_end)
    return round(total, 2)


def periods_without_grid_charge(periods: list[ChargePeriodConfig]) -> list[ChargePeriodConfig]:
    """Storm schedule with force charge but no grid import (PV top-up only)."""
    out: list[ChargePeriodConfig] = []
    for period in periods:
        copy = ChargePeriodConfig.from_dict(period.to_dict())
        if copy.enable_force_charge:
            copy.enable_charge_from_grid = False
        out.append(copy)
    return out


def evaluate_storm_solcast_precheck(
    *,
    cfg: Any,
    solcast_configured: bool,
    forecast_rows: list[dict[str, Any]],
    condition_active: bool,
    forecast_active: bool,
    forecast_detail: dict[str, Any] | None,
    soc_pct: float | None,
    capacity_kwh: float | None,
    kwh_remaining: float | None,
) -> dict[str, Any]:
    """Advise whether grid pre-charge is needed before a forecast storm."""
    base_periods = list(getattr(cfg, "charge_periods", []) or [])
    target_soc = _target_soc_pct(cfg)
    margin = float(getattr(cfg, "solcast_safety_margin", 1.35) or 1.35)
    min_soc_floor = float(getattr(cfg, "solcast_min_soc_floor", 90.0) or 90.0)
    use_limit = bool(getattr(cfg, "use_solcast_grid_limit", False))
    hours_until = _hours_until_storm(forecast_detail)

    deficit = battery_deficit_kwh(
        soc_pct=soc_pct,
        capacity_kwh=capacity_kwh,
        kwh_remaining=kwh_remaining,
        target_soc_pct=target_soc,
    )

    out: dict[str, Any] = {
        "feature_enabled": use_limit,
        "solcast_configured": solcast_configured,
        "condition_active": condition_active,
        "forecast_active": forecast_active,
        "hours_until_storm": hours_until,
        "target_soc_pct": round(target_soc, 1),
        "min_soc_floor_pct": round(min_soc_floor, 1),
        "safety_margin": round(margin, 2),
        "deficit_kwh": round(deficit, 2) if deficit is not None else None,
        "soc_pct": round(soc_pct, 1) if soc_pct is not None else None,
        "pv_before_storm_kwh": None,
        "effective_pv_kwh": None,
        "action": ACTION_DISABLED,
        "summary": "",
        "detail": "",
        "periods": base_periods,
    }

    if not use_limit:
        out["action"] = ACTION_DISABLED
        out["summary"] = (
            "Solcast grid limit is off — StormSafe will use full grid pre-charge when armed."
        )
        out["detail"] = (
            "Turn on the option below to skip or reduce grid import when Solcast predicts "
            "enough solar before the storm."
        )
        return out

    if not solcast_configured:
        out["action"] = ACTION_UNAVAILABLE
        out["summary"] = "Solcast is not configured — full grid pre-charge when StormSafe arms."
        out["detail"] = (
            "Configure Solcast under Settings → Solcast (API key and PV strings) "
            "to enable PV-aware pre-charge."
        )
        return out

    if condition_active:
        out["action"] = ACTION_FULL_GRID
        out["summary"] = (
            "Storm conditions are active now — full grid pre-charge applies "
            "(Solcast limit is not used during active storms)."
        )
        out["detail"] = (
            "When the inverter is already in a storm-type weather state, StormSafe "
            "always uses your storm settings with grid import enabled."
        )
        return out

    if not forecast_active:
        out["action"] = ACTION_UNAVAILABLE
        out["summary"] = "No storm in the forecast window — nothing to pre-check yet."
        out["detail"] = (
            "When Google Weather forecasts severe weather within your lead time, "
            "this section shows whether PV can cover the battery gap before grid import is used."
        )
        return out

    if deficit is None:
        out["action"] = ACTION_FULL_GRID
        out["summary"] = "Battery level unknown — full grid pre-charge if StormSafe arms."
        out["detail"] = "SOC or capacity sensors were unavailable for the calculation."
        return out

    if soc_pct is not None and soc_pct < min_soc_floor:
        out["action"] = ACTION_FULL_GRID
        out["summary"] = (
            f"Battery at {soc_pct:.0f}% is below the {min_soc_floor:.0f}% safety floor — "
            "grid pre-charge recommended."
        )
        out["detail"] = (
            "Even when Solcast shows solar before the storm, StormSafe will grid pre-charge "
            "until SOC is at or above the minimum floor you set."
        )
        return out

    if deficit <= 0.05:
        out["action"] = ACTION_PV_ONLY
        out["periods"] = periods_without_grid_charge(base_periods)
        out["summary"] = (
            f"Battery already at target ({target_soc:.0f}%) — no grid pre-charge needed."
        )
        out["detail"] = "StormSafe may still arm for monitoring; grid import is not required."
        return out

    now = dt_util.now()
    if hours_until is not None and hours_until > 0:
        window_end = now + timedelta(hours=hours_until)
    else:
        window_end = now + timedelta(hours=1.0)

    pv_kwh = _pv_kwh_before(forecast_rows, window_end=window_end)
    out["pv_before_storm_kwh"] = pv_kwh
    if pv_kwh is None:
        out["action"] = ACTION_FULL_GRID
        out["summary"] = "Solcast forecast unavailable — full grid pre-charge if StormSafe arms."
        out["detail"] = "Refresh the Solcast forecast under Settings → Solcast."
        return out

    effective_pv = round(pv_kwh / margin, 2) if margin > 0 else pv_kwh
    out["effective_pv_kwh"] = effective_pv

    window_label = f"~{hours_until:.1f}h" if hours_until is not None else "before storm"
    if effective_pv >= deficit:
        out["action"] = ACTION_PV_ONLY
        out["periods"] = periods_without_grid_charge(base_periods)
        out["summary"] = (
            f"Need {deficit:.1f} kWh to reach {target_soc:.0f}%. Solcast predicts "
            f"{pv_kwh:.1f} kWh solar {window_label} "
            f"(×{margin:.2f} margin → {effective_pv:.1f} kWh effective). "
            "PV should cover the gap — grid pre-charge not required."
        )
        out["detail"] = (
            "If you turn this option off, StormSafe will grid pre-charge anyway when armed. "
            "If storm conditions become active, full grid pre-charge will apply automatically."
        )
    else:
        out["action"] = ACTION_FULL_GRID
        shortfall = round(max(0.0, deficit - effective_pv), 2)
        out["summary"] = (
            f"Need {deficit:.1f} kWh to reach {target_soc:.0f}%. Solcast predicts "
            f"{pv_kwh:.1f} kWh solar {window_label} "
            f"(×{margin:.2f} margin → {effective_pv:.1f} kWh effective). "
            f"Shortfall ~{shortfall:.1f} kWh — grid pre-charge recommended."
        )
        out["detail"] = (
            "Turning this option off does not change that recommendation — "
            "StormSafe will grid pre-charge when armed. "
            "Only enable PV-only mode when you accept the backup risk."
        )

    return out
