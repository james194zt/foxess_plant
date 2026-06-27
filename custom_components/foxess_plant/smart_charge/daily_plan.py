"""Daily plan builder — spread optimizer, charge, export, and idle slots."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .context import build_context, config_float
from .grid_charge import _merge_slots
from .spread import optimize_spread_plan
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
    carbon_periods: list[dict[str, Any]] | None = None,
    greener_nights: list[dict[str, Any]] | None = None,
    tariff_type: str | None = None,
) -> list[dict[str, Any]]:
    """Build plan from current Agile rates and Solcast (rest-of-today before daily plan time)."""
    ctx = build_context(
        config=config,
        soc_pct=soc_pct,
        capacity_kwh=capacity_kwh,
        kwh_remaining=kwh_remaining,
        forecast_rows=forecast_rows,
        live_load_kw=live_load_kw,
        horizon_hours=horizon_hours,
        tariff_type=tariff_type,
    )

    now = dt_util.utcnow()
    end = plan_horizon_end(config=config, horizon_hours=horizon_hours, when=now)
    horizon_slots = [s for s in _merge_slots(import_slots) if s.end > now and s.start < end]

    plan, pairs = optimize_spread_plan(
        config=config,
        slots=horizon_slots,
        ctx=ctx,
        forecast_rows=forecast_rows,
        horizon_hours=horizon_hours,
        carbon_periods=carbon_periods,
        greener_nights=greener_nights,
        exportable_kwh=exportable_kwh,
    )

    meta = {
        "operating_mode": ctx["operating_mode"],
        "grid_gap_kwh": ctx["grid_gap_kwh"],
        "reserve_kwh": ctx["reserve_kwh"],
        "plan_horizon": "24h" if is_after_daily_plan_time(config) else "rest_of_today",
        "spread_pairs": pairs,
        "spread_optimizer": bool(getattr(config, "spread_optimizer_enabled", True)),
        "expected_spread_profit_p": round(sum(p.get("spread_p_per_kwh", 0) for p in pairs), 2)
        if pairs
        else None,
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
            if start_s == end_s:
                end = start + timedelta(minutes=30)
            elif end <= start:
                end += timedelta(days=1)
            if start <= local_now < end:
                return entry
        except (TypeError, ValueError, IndexError):
            continue
    return None


__all__ = [
    "build_daily_plan",
    "current_plan_slot",
    "is_after_daily_plan_time",
    "plan_horizon_end",
]
