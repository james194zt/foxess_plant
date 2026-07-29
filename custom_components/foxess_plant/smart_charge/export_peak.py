"""Export during high Agile export rates — Force Discharge windows."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .export_limits import export_allowed_for_mode, mode_export_limits
from .export_slot_pick import pick_best_export_slot
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
    lookahead_minutes: int = 720,
) -> RateSlot | None:
    """Pick the highest export-priced half-hour above the threshold in the lookahead.

    Threshold alone is not enough — if 18:00 is 18p and 19:00 is 21p (both above
    min_export_p), we wait for 19:00 rather than exporting early at the weaker rate.
    Default lookahead is 12h so evening peaks are visible from the afternoon.
    """
    current = dt_util.utcnow() if now is None else dt_util.as_utc(now)
    horizon = current + timedelta(minutes=max(30, lookahead_minutes))
    return pick_best_export_slot(
        _merge_slots(slots),
        min_export_p=min_export_p,
        current=current,
        horizon=horizon,
    )


def slot_window_dict(slot: RateSlot) -> dict[str, Any]:
    export_p = slot.export_p_per_kwh
    return {
        "start": _fmt_hhmm(slot.start),
        "end": _fmt_hhmm(slot.end),
        "export_p_per_kwh": round(export_p, 4) if export_p is not None else None,
        "import_p_per_kwh": round(slot.import_p_per_kwh, 4),
    }


def discharge_window_active_now(
    window: dict[str, Any] | None,
    when: datetime | None = None,
    *,
    early_minutes: int = 1,
) -> bool:
    """True when local clock is inside (or just before) an export HH:MM window.

    Force Discharge is applied immediately when armed — only arm while this is True
    so a future peak slot is not discharged early.
    """
    if not window:
        return False
    start_s = str(window.get("start") or "").strip()
    end_s = str(window.get("end") or "").strip()
    if not start_s or not end_s:
        return False
    try:
        start_h, start_m = (int(x) for x in start_s.split(":")[:2])
        end_h, end_m = (int(x) for x in end_s.split(":")[:2])
    except (TypeError, ValueError):
        return False
    local_now = dt_util.as_local(when or dt_util.now())
    early = timedelta(minutes=max(0, int(early_minutes)))
    start = local_now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end = local_now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if start_s == end_s:
        end = start + timedelta(minutes=30)
    elif end <= start:
        end += timedelta(days=1)
    if end <= local_now - early:
        start += timedelta(days=1)
        end += timedelta(days=1)
    return start - early <= local_now < end


def evaluate_export_discharge(
    *,
    config: Any,
    slot: RateSlot,
    ctx: dict[str, Any],
    forecast_rows: list[dict[str, Any]],
    horizon_hours: float,
    eval_tier: str,
    daily_plan: list[dict[str, Any]] | None = None,
    soc_pct: float | None = None,
) -> SmartChargeDecision | None:
    operating_mode = ctx["operating_mode"]
    if not export_allowed_for_mode(operating_mode, config):
        return None

    from .reserve import export_floor_reached

    export_min_soc = ctx.get("export_min_soc")
    if export_min_soc is None:
        export_min_soc = _config_float(config, "export_min_soc", 40.0)
    live_soc = soc_pct if soc_pct is not None else ctx.get("soc_pct")
    if export_floor_reached(soc_pct=live_soc, export_min_soc=export_min_soc):
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
    solar_covers = solcast_covers_export_recharge(
        forecast_rows,
        export_kwh=export_kwh,
        solar_safety_margin=margin,
        horizon_hours=horizon_hours,
    )
    # Peak/surplus export: allow when SOC is above the virtual floor even if Solcast
    # will not fully recharge the exported energy today (avoids missing 24p+ windows).
    if not solar_covers and live_soc is None:
        return None

    window = slot_window_dict(slot)
    reason_suffix = "solar can recharge" if solar_covers else "surplus above export floor"
    return SmartChargeDecision(
        action="export_discharge",
        reason=(
            f"Export {window['start']}-{window['end']} at {export_p:.2f}p/kWh "
            f"({export_kwh:.1f} kWh, {reason_suffix})"
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
