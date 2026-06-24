"""SmartCharge strategy engine — operating modes, reserve floor, export, daily plan."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from ..models import ChargePeriodConfig
from .context import build_context
from .daily_plan import build_daily_plan, current_plan_slot
from .export_peak import evaluate_export_discharge, find_export_slot, mode_export_limits
from .grid_charge import (
    _periods_from_block,
    battery_deficit_kwh,
    evaluate_grid_charge,
    find_negative_import_slot,
)
from .types import RateSlot, SmartChargeDecision


CHARGE_PLAN_ACTIONS = frozenset({"charge", "spread_charge", "winter_fill", "charge_candidate", "arbitrage"})
EXPORT_PLAN_ACTIONS = frozenset({"export", "spread_export"})
SOLAR_GAP_FILL_REASONS = frozenset({"winter_fill", "solar_gap_fill"})


def _spread_meta_from_plan(daily_plan: list[dict[str, Any]] | None) -> tuple[list[dict[str, Any]], float | None]:
    if not daily_plan:
        return [], None
    head = daily_plan[0]
    pairs = head.get("spread_pairs") if isinstance(head.get("spread_pairs"), list) else []
    profit = head.get("expected_spread_profit_p")
    return pairs, float(profit) if profit is not None else None


def _attach_spread_meta(decision: SmartChargeDecision, daily_plan: list[dict[str, Any]] | None) -> SmartChargeDecision:
    pairs, profit = _spread_meta_from_plan(daily_plan)
    if pairs:
        decision.spread_pairs = pairs
    if profit is not None:
        decision.planned_spread_profit_p = profit
    return decision


def _config_bool(config: Any, key: str, default: bool) -> bool:
    value = getattr(config, key, default)
    if value is None:
        return default
    return bool(value)


def _fmt_hhmm_local(when: datetime) -> str:
    return dt_util.as_local(when).strftime("%H:%M")


def _plan_slot_window_label(
    plan_slot: dict[str, Any],
    charge_slot: RateSlot | None,
) -> str:
    if charge_slot is not None:
        start = _fmt_hhmm_local(charge_slot.start)
        end = _fmt_hhmm_local(charge_slot.end)
        if start != end:
            return f"{start}-{end}"
        if charge_slot.duration_hours > 0:
            return start
    start_s = str(plan_slot.get("start") or "?")
    end_s = str(plan_slot.get("end") or "?")
    if start_s != end_s:
        return f"{start_s}-{end_s}"
    return start_s


def _daily_plan_charge_reason(
    plan_slot: dict[str, Any],
    charge_slot: RateSlot | None,
) -> str:
    window = _plan_slot_window_label(plan_slot, charge_slot)
    plan_reason = plan_slot.get("reason") or "daily_plan"
    if plan_reason in SOLAR_GAP_FILL_REASONS:
        return f"Solar gap fill {window}"
    if plan_reason == "spread_pair":
        return f"Spread charge {window}"
    return f"Daily plan {window}"


def _slot_from_plan_entry(
    entry: dict[str, Any],
    import_slots: list[RateSlot],
) -> RateSlot | None:
    start_s = entry.get("start")
    end_s = entry.get("end")
    if not start_s or not end_s:
        return None
    for slot in import_slots:
        if _fmt_hhmm_local(slot.start) == start_s and _fmt_hhmm_local(slot.end) == end_s:
            return slot
    local_now = dt_util.as_local(dt_util.now())
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
        import_p = float(entry.get("import_p_per_kwh") or 0)
        export_raw = entry.get("export_p_per_kwh")
        export_p = float(export_raw) if export_raw is not None else None
        return RateSlot(
            start=dt_util.as_utc(start),
            end=dt_util.as_utc(end),
            import_p_per_kwh=import_p,
            export_p_per_kwh=export_p,
        )
    except (TypeError, ValueError, IndexError):
        return None


def _negative_import_decision(
    *,
    config: Any,
    slot: RateSlot,
    ctx: dict[str, Any],
    soc_pct: float | None,
    capacity_kwh: float | None,
    kwh_remaining: float | None,
    forecast_rows: list[dict[str, Any]],
    import_slots: list[RateSlot],
    export_slots: list[RateSlot] | None,
    daily_plan: list[dict[str, Any]] | None,
) -> SmartChargeDecision:
    templates = list(getattr(config, "charge_periods", []) or [])
    if len(templates) < 2:
        templates = templates + [ChargePeriodConfig()] * (2 - len(templates))
    periods = _periods_from_block([slot], templates)
    import_p = slot.import_p_per_kwh
    decision = evaluate_grid_charge(
        config=config,
        soc_pct=soc_pct,
        capacity_kwh=capacity_kwh,
        kwh_remaining=kwh_remaining,
        forecast_rows=forecast_rows,
        import_slots=import_slots,
        export_slots=export_slots,
        target_soc_pct=ctx["target_soc_pct"],
        reserve_kwh=ctx["reserve_kwh"],
        exportable_kwh=ctx["exportable_kwh"],
        operating_mode=ctx["operating_mode"],
        grid_gap_kwh=ctx["grid_gap_kwh"],
        dark_hours_kwh=ctx["dark_hours_kwh"],
        eval_tier="negative_interrupt",
        daily_plan=daily_plan,
    )
    if decision.action in ("skip", "idle"):
        return SmartChargeDecision(
            action="arbitrage",
            reason=f"Negative import interrupt {import_p:.2f}p/kWh",
            charge_periods=periods,
            target_max_soc=decision.target_max_soc,
            deficit_kwh=decision.deficit_kwh,
            forecast_kwh=decision.forecast_kwh,
            windows=[
                {
                    "start": _fmt_hhmm_local(slot.start),
                    "end": _fmt_hhmm_local(slot.end),
                    "import_p_per_kwh": round(import_p, 4),
                }
            ],
            operating_mode=ctx["operating_mode"],
            reserve_kwh=ctx["reserve_kwh"],
            exportable_kwh=ctx["exportable_kwh"],
            target_soc_effective=ctx["target_soc_pct"],
            grid_gap_kwh=ctx["grid_gap_kwh"],
            dark_hours_kwh=ctx["dark_hours_kwh"],
            daily_plan=daily_plan or [],
            eval_tier="negative_interrupt",
        )
    decision.action = "arbitrage"
    decision.reason = f"Negative import interrupt {import_p:.2f}p/kWh ({decision.deficit_kwh or 0:.1f} kWh deficit)"
    decision.charge_periods = periods
    decision.windows = [
        {
            "start": _fmt_hhmm_local(slot.start),
            "end": _fmt_hhmm_local(slot.end),
            "import_p_per_kwh": round(import_p, 4),
        }
    ]
    decision.eval_tier = "negative_interrupt"
    return decision


def _try_export_decision(
    *,
    config: Any,
    ctx: dict[str, Any],
    forecast_rows: list[dict[str, Any]],
    import_slots: list[RateSlot],
    daily_plan: list[dict[str, Any]] | None,
    horizon_hours: float,
    plan_slot: dict[str, Any] | None,
    soc_pct: float | None,
    capacity_kwh: float | None,
    kwh_remaining: float | None,
) -> SmartChargeDecision | None:
    deficit = battery_deficit_kwh(
        soc_pct=soc_pct,
        capacity_kwh=capacity_kwh,
        kwh_remaining=kwh_remaining,
        target_soc_pct=ctx["target_soc_pct"],
    )
    min_deficit = float(getattr(config, "min_deficit_kwh", 0.5) or 0.5)
    if deficit is not None and deficit > min_deficit:
        return None

    min_export_p, _ = mode_export_limits(ctx["operating_mode"], config)
    slot: RateSlot | None = None
    eval_tier = "tactical"
    if plan_slot and plan_slot.get("action") in EXPORT_PLAN_ACTIONS:
        slot = _slot_from_plan_entry(plan_slot, import_slots)
        eval_tier = "daily_plan"
    if slot is None:
        slot = find_export_slot(import_slots, min_export_p=min_export_p)
    if slot is None:
        return None
    return evaluate_export_discharge(
        config=config,
        slot=slot,
        ctx=ctx,
        forecast_rows=forecast_rows,
        horizon_hours=horizon_hours,
        eval_tier=eval_tier,
        daily_plan=daily_plan,
    )


def evaluate_smart_charge(
    *,
    config: Any,
    soc_pct: float | None,
    capacity_kwh: float | None,
    kwh_remaining: float | None,
    forecast_rows: list[dict[str, Any]],
    import_slots: list[RateSlot],
    export_slots: list[RateSlot] | None = None,
    live_load_kw: float | None = None,
    daily_plan: list[dict[str, Any]] | None = None,
    horizon_hours: float = 24.0,
    tariff_type: str | None = None,
) -> SmartChargeDecision:
    """Strategy entry — reserve floor, export peaks, house-load budget, tactical interrupts."""
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

    if _config_bool(config, "negative_import_interrupt", True):
        neg_slot = find_negative_import_slot(import_slots)
        if neg_slot is not None:
            return _negative_import_decision(
                config=config,
                slot=neg_slot,
                ctx=ctx,
                soc_pct=soc_pct,
                capacity_kwh=capacity_kwh,
                kwh_remaining=kwh_remaining,
                forecast_rows=forecast_rows,
                import_slots=import_slots,
                export_slots=export_slots,
                daily_plan=daily_plan,
            )

    plan_slot = current_plan_slot(daily_plan)
    pairs, _ = _spread_meta_from_plan(daily_plan)

    if plan_slot and plan_slot.get("action") in CHARGE_PLAN_ACTIONS:
        charge_slot = _slot_from_plan_entry(plan_slot, import_slots)
        if charge_slot is not None:
            templates = list(getattr(config, "charge_periods", []) or [])
            if len(templates) < 2:
                templates = templates + [ChargePeriodConfig()] * (2 - len(templates))
            periods = _periods_from_block([charge_slot], templates)
            reason = _daily_plan_charge_reason(plan_slot, charge_slot)
            decision = evaluate_grid_charge(
                config=config,
                soc_pct=soc_pct,
                capacity_kwh=capacity_kwh,
                kwh_remaining=kwh_remaining,
                forecast_rows=forecast_rows,
                import_slots=import_slots,
                export_slots=export_slots,
                target_soc_pct=ctx["target_soc_pct"],
                reserve_kwh=ctx["reserve_kwh"],
                exportable_kwh=ctx["exportable_kwh"],
                operating_mode=ctx["operating_mode"],
                grid_gap_kwh=ctx["grid_gap_kwh"],
                dark_hours_kwh=ctx["dark_hours_kwh"],
                eval_tier="daily_plan",
                daily_plan=daily_plan,
            )
            if decision.action in ("grid_charge", "arbitrage"):
                decision.reason = reason
                decision.charge_periods = periods
                decision.eval_tier = "daily_plan"
                return _attach_spread_meta(decision, daily_plan)
            if decision.action in ("skip", "idle"):
                decision.reason = f"{reason} — not charging: {decision.reason}"
                decision.eval_tier = "daily_plan"
                return _attach_spread_meta(decision, daily_plan)

    export_decision = _try_export_decision(
        config=config,
        ctx=ctx,
        forecast_rows=forecast_rows,
        import_slots=import_slots,
        daily_plan=daily_plan,
        horizon_hours=horizon_hours,
        plan_slot=plan_slot,
        soc_pct=soc_pct,
        capacity_kwh=capacity_kwh,
        kwh_remaining=kwh_remaining,
    )
    if export_decision is not None:
        return _attach_spread_meta(export_decision, daily_plan)

    eval_tier = "daily_plan" if plan_slot else "tactical"
    decision = evaluate_grid_charge(
        config=config,
        soc_pct=soc_pct,
        capacity_kwh=capacity_kwh,
        kwh_remaining=kwh_remaining,
        forecast_rows=forecast_rows,
        import_slots=import_slots,
        export_slots=export_slots,
        target_soc_pct=ctx["target_soc_pct"],
        reserve_kwh=ctx["reserve_kwh"],
        exportable_kwh=ctx["exportable_kwh"],
        operating_mode=ctx["operating_mode"],
        grid_gap_kwh=ctx["grid_gap_kwh"],
        dark_hours_kwh=ctx["dark_hours_kwh"],
        eval_tier=eval_tier,
        daily_plan=daily_plan,
    )
    return _attach_spread_meta(decision, daily_plan)


__all__ = [
    "build_daily_plan",
    "evaluate_smart_charge",
]
