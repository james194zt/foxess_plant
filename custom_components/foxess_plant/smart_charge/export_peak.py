"""Export during high Agile export rates — Force Discharge windows."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .export_limits import export_allowed_for_mode, mode_export_limits
from .grid_charge import _fmt_hhmm, _merge_slots
from .solcast_remaining import solcast_forecast_kwh_for_horizon
from .types import RateSlot, SmartChargeDecision


def _config_float(config: Any, key: str, default: float) -> float:
    try:
        return float(getattr(config, key, default) or default)
    except (TypeError, ValueError):
        return default


def solcast_covers_export_recharge(
    forecast_rows: list[dict[str, Any]],
    *,
    export_kwh: float,
    solar_safety_margin: float,
    horizon_hours: float = 24.0,
) -> bool:
    forecast_kwh = solcast_forecast_kwh_for_horizon(forecast_rows, horizon_hours=horizon_hours)
    if forecast_kwh is None:
        return False
    margin = max(1.0, solar_safety_margin)
    return forecast_kwh / margin >= max(0.0, export_kwh)


def planned_export_kwh(
    *,
    exportable_kwh: float | None,
    slot: RateSlot,
    operating_mode: str,
    config: Any,
) -> float | None:
    if exportable_kwh is None or exportable_kwh <= 0:
        return None
    _min_p, fraction = mode_export_limits(operating_mode, config)
    min_kwh = _config_float(config, "min_export_kwh", 0.5)
    cap = exportable_kwh * max(0.0, min(1.0, fraction))
    slot_kwh = cap
    if slot.duration_hours > 0:
        slot_kwh = min(cap, exportable_kwh)
    if slot_kwh < min_kwh:
        return None
    return round(slot_kwh, 2)


def find_export_slot(
    slots: list[RateSlot],
    *,
    min_export_p: float,
    now: datetime | None = None,
    lookahead_minutes: int = 35,
) -> RateSlot | None:
    current = dt_util.utcnow() if now is None else dt_util.as_utc(now)
    horizon = current + timedelta(minutes=max(30, lookahead_minutes))
    best: RateSlot | None = None
    best_p = -999.0
    for slot in _merge_slots(slots):
        if slot.end <= current or slot.start >= horizon:
            continue
        export_p = slot.export_p_per_kwh
        if export_p is None or export_p < min_export_p:
            continue
        if export_p > best_p:
            best_p = export_p
            best = slot
    return best


def slot_window_dict(slot: RateSlot) -> dict[str, Any]:
    export_p = slot.export_p_per_kwh
    return {
        "start": _fmt_hhmm(slot.start),
        "end": _fmt_hhmm(slot.end),
        "export_p_per_kwh": round(export_p, 4) if export_p is not None else None,
        "import_p_per_kwh": round(slot.import_p_per_kwh, 4),
    }


def evaluate_export_discharge(
    *,
    config: Any,
    slot: RateSlot,
    ctx: dict[str, Any],
    forecast_rows: list[dict[str, Any]],
    horizon_hours: float,
    eval_tier: str,
    daily_plan: list[dict[str, Any]] | None = None,
) -> SmartChargeDecision | None:
    operating_mode = ctx["operating_mode"]
    if not export_allowed_for_mode(operating_mode, config):
        return None

    min_export_p, _fraction = mode_export_limits(operating_mode, config)
    export_p = slot.export_p_per_kwh
    if export_p is None or export_p < min_export_p:
        return None

    export_kwh = planned_export_kwh(
        exportable_kwh=ctx.get("exportable_kwh"),
        slot=slot,
        operating_mode=operating_mode,
        config=config,
    )
    if export_kwh is None:
        return None

    margin = _config_float(config, "solar_safety_margin", 1.15)
    if not solcast_covers_export_recharge(
        forecast_rows,
        export_kwh=export_kwh,
        solar_safety_margin=margin,
        horizon_hours=horizon_hours,
    ):
        return None

    window = slot_window_dict(slot)
    return SmartChargeDecision(
        action="export_discharge",
        reason=(
            f"Export {window['start']}-{window['end']} at {export_p:.2f}p/kWh "
            f"({export_kwh:.1f} kWh above reserve)"
        ),
        windows=[window],
        discharge_window=window,
        work_mode_target="Force Discharge",
        planned_export_kwh=export_kwh,
        operating_mode=operating_mode,
        reserve_kwh=ctx.get("reserve_kwh"),
        exportable_kwh=ctx.get("exportable_kwh"),
        target_soc_effective=ctx.get("target_soc_pct"),
        grid_gap_kwh=ctx.get("grid_gap_kwh"),
        dark_hours_kwh=ctx.get("dark_hours_kwh"),
        daily_plan=daily_plan or [],
        eval_tier=eval_tier,
    )
