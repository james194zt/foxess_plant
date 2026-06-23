"""Daily plan builder — charge, export, and idle slots for next 24h."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .export_limits import export_allowed_for_mode, mode_export_limits
from .export_peak import planned_export_kwh, solcast_covers_export_recharge
from .context import build_context, config_float
from .grid_charge import _fmt_hhmm, _merge_slots
from .types import RateSlot


def is_after_daily_plan_time(config: Any, when: datetime | None = None) -> bool:
    local = dt_util.as_local(when or dt_util.now())
    plan_time = str(getattr(config, "daily_plan_time", "16:00") or "16:00")
    try:
        hour_s, minute_s = plan_time.split(":", 1)
        hour = int(hour_s)
        minute = int(minute_s)
    except (TypeError, ValueError):
        hour, minute = 16, 0
    boundary = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return local >= boundary


def plan_horizon_end(
    *,
    config: Any,
    horizon_hours: float,
    when: datetime | None = None,
) -> datetime:
    now = dt_util.as_utc(when or dt_util.utcnow())
    full_horizon = now + timedelta(hours=horizon_hours)
    if is_after_daily_plan_time(config, when):
        return full_horizon
    local = dt_util.as_local(now)
    midnight = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return min(full_horizon, dt_util.as_utc(midnight))


def build_daily_plan(
    *,
    config: Any,
    import_slots: list[RateSlot],
    forecast_rows: list[dict[str, Any]],
    live_load_kw: float | None,
    horizon_hours: float = 24.0,
    exportable_kwh: float | None = None,
    capacity_kwh: float | None = None,
    kwh_remaining: float | None = None,
    soc_pct: float | None = None,
) -> list[dict[str, Any]]:
    """Build next 24h plan (or rest-of-today before daily plan time) with export peaks."""
    ctx = build_context(
        config=config,
        soc_pct=soc_pct,
        capacity_kwh=capacity_kwh,
        kwh_remaining=kwh_remaining,
        forecast_rows=forecast_rows,
        live_load_kw=live_load_kw,
        horizon_hours=horizon_hours,
    )
    exportable = exportable_kwh if exportable_kwh is not None else ctx.get("exportable_kwh")
    operating_mode = ctx["operating_mode"]
    min_export_p, _ = mode_export_limits(operating_mode, config)
    margin = config_float(config, "solar_safety_margin", 1.15)
    allow_export = export_allowed_for_mode(operating_mode, config)

    now = dt_util.utcnow()
    end = plan_horizon_end(config=config, horizon_hours=horizon_hours, when=now)
    plan: list[dict[str, Any]] = []
    for slot in _merge_slots(import_slots):
        if slot.end <= now or slot.start >= end:
            continue
        export_p = slot.export_p_per_kwh
        entry: dict[str, Any] = {
            "start": _fmt_hhmm(slot.start),
            "end": _fmt_hhmm(slot.end),
            "import_p_per_kwh": round(slot.import_p_per_kwh, 4),
            "export_p_per_kwh": round(export_p, 4) if export_p is not None else None,
        }
        if slot.import_p_per_kwh < 0:
            entry["action"] = "charge"
            entry["reason"] = "negative_import"
        elif allow_export and export_p is not None and export_p >= min_export_p:
            export_kwh = planned_export_kwh(
                exportable_kwh=exportable,
                slot=slot,
                operating_mode=operating_mode,
                config=config,
            )
            if export_kwh and solcast_covers_export_recharge(
                forecast_rows,
                export_kwh=export_kwh,
                solar_safety_margin=margin,
                horizon_hours=horizon_hours,
            ):
                entry["action"] = "export"
                entry["reason"] = "high_export"
                entry["planned_export_kwh"] = export_kwh
            elif slot.import_p_per_kwh <= 5.0:
                entry["action"] = "charge_candidate"
                entry["reason"] = "cheap_import"
            else:
                entry["action"] = "idle"
                entry["reason"] = "hold"
        elif slot.import_p_per_kwh <= 5.0:
            entry["action"] = "charge_candidate"
            entry["reason"] = "cheap_import"
        else:
            entry["action"] = "idle"
            entry["reason"] = "hold"
        plan.append(entry)

    meta = {
        "operating_mode": operating_mode,
        "grid_gap_kwh": ctx["grid_gap_kwh"],
        "reserve_kwh": ctx["reserve_kwh"],
        "plan_horizon": "24h" if is_after_daily_plan_time(config) else "rest_of_today",
    }
    if plan:
        plan[0].update(meta)
    else:
        plan.append({"action": "idle", "reason": "no_slots", **meta})
    return plan


def current_plan_slot(
    daily_plan: list[dict[str, Any]] | None,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    if not daily_plan:
        return None
    local_now = dt_util.as_local(now or dt_util.now())
    for entry in daily_plan:
        if entry.get("action") == "idle" and entry.get("reason") == "no_slots":
            continue
        start_s = entry.get("start")
        end_s = entry.get("end")
        if not start_s or not end_s:
            continue
        try:
            start = local_now.replace(
                hour=int(start_s.split(":")[0]),
                minute=int(start_s.split(":")[1]),
                second=0,
                microsecond=0,
            )
            end = local_now.replace(
                hour=int(end_s.split(":")[0]),
                minute=int(end_s.split(":")[1]),
                second=0,
                microsecond=0,
            )
            if end <= start:
                end += timedelta(days=1)
            if start <= local_now < end:
                return entry
        except (TypeError, ValueError, IndexError):
            continue
    return None
