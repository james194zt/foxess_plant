"""SmartCharge strategy engine — operating modes, reserve floor, daily plan scaffold."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from ..models import ChargePeriodConfig
from .grid_charge import (
    _fmt_hhmm,
    _merge_slots,
    _periods_from_block,
    evaluate_grid_charge,
    find_negative_import_slot,
)
from .reserve import OPERATING_MODE_MAX_SAFETY, compute_exportable_kwh, compute_outage_reserve_kwh
from .solcast_budget import compute_house_energy_budget
from .types import RateSlot, SmartChargeDecision


def _config_float(config: Any, key: str, default: float) -> float:
    try:
        return float(getattr(config, key, default) or default)
    except (TypeError, ValueError):
        return default


def _config_bool(config: Any, key: str, default: bool) -> bool:
    value = getattr(config, key, default)
    if value is None:
        return default
    return bool(value)


def _effective_home_load_kw(config: Any, live_load_kw: float | None) -> float:
    reserve_load = getattr(config, "outage_reserve_load_kw", None)
    if reserve_load is not None:
        try:
            return max(0.0, float(reserve_load))
        except (TypeError, ValueError):
            pass
    if live_load_kw is not None and live_load_kw > 0:
        return live_load_kw
    return _config_float(config, "house_load_kw_fallback", 1.0)


def _max_target_soc(config: Any) -> float:
    explicit = getattr(config, "max_target_soc", None)
    if explicit is not None:
        return min(100.0, max(10.0, float(explicit)))
    return min(100.0, max(10.0, _config_float(config, "target_soc", 100.0)))


def _build_context(
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
    load_kw = _effective_home_load_kw(config, live_load_kw)
    reserve_kwh = compute_outage_reserve_kwh(
        avg_home_load_kw=load_kw,
        vulnerable_hours=_config_float(config, "outage_reserve_hours", 3.0),
        safety_margin=_config_float(config, "outage_reserve_margin", 1.2),
        operating_mode=operating_mode,
        safety_reserve_multiplier=_config_float(config, "safety_reserve_multiplier", 1.5),
    )
    exportable_kwh = compute_exportable_kwh(kwh_remaining=kwh_remaining, reserve_kwh=reserve_kwh)
    budget = compute_house_energy_budget(
        forecast_rows=forecast_rows,
        avg_home_load_kw=load_kw,
        dark_hours_estimate=_config_float(config, "dark_hours_estimate", 8.0),
        solar_safety_margin=_config_float(config, "solar_safety_margin", 1.15),
        capacity_kwh=capacity_kwh,
        max_target_soc=_max_target_soc(config),
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


def build_daily_plan(
    *,
    config: Any,
    import_slots: list[RateSlot],
    forecast_rows: list[dict[str, Any]],
    live_load_kw: float | None,
    horizon_hours: float = 24.0,
) -> list[dict[str, Any]]:
    """Phase-1 scaffold: annotate next 24h half-hour slots for panel diagnostics."""
    ctx = _build_context(
        config=config,
        soc_pct=None,
        capacity_kwh=None,
        kwh_remaining=None,
        forecast_rows=forecast_rows,
        live_load_kw=live_load_kw,
        horizon_hours=horizon_hours,
    )
    now = dt_util.utcnow()
    end = now + timedelta(hours=horizon_hours)
    plan: list[dict[str, Any]] = []
    for slot in _merge_slots(import_slots):
        if slot.end <= now or slot.start >= end:
            continue
        if slot.import_p_per_kwh < 0:
            action = "charge"
            reason = "negative_import"
        elif slot.import_p_per_kwh <= 5.0:
            action = "charge_candidate"
            reason = "cheap_import"
        else:
            action = "idle"
            reason = "hold"
        plan.append(
            {
                "start": _fmt_hhmm(slot.start),
                "end": _fmt_hhmm(slot.end),
                "action": action,
                "reason": reason,
                "import_p_per_kwh": round(slot.import_p_per_kwh, 4),
                "export_p_per_kwh": round(slot.export_p_per_kwh, 4)
                if slot.export_p_per_kwh is not None
                else None,
            }
        )
    if plan:
        plan[0]["operating_mode"] = ctx["operating_mode"]
        plan[0]["grid_gap_kwh"] = ctx["grid_gap_kwh"]
    return plan


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
                    "start": _fmt_hhmm(slot.start),
                    "end": _fmt_hhmm(slot.end),
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
            "start": _fmt_hhmm(slot.start),
            "end": _fmt_hhmm(slot.end),
            "import_p_per_kwh": round(import_p, 4),
        }
    ]
    decision.eval_tier = "negative_interrupt"
    return decision


def _current_plan_slot(
    daily_plan: list[dict[str, Any]] | None,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    if not daily_plan:
        return None
    local_now = dt_util.as_local(now or dt_util.now())
    for entry in daily_plan:
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
) -> SmartChargeDecision:
    """Strategy entry — reserve floor, house-load budget, tactical interrupts."""
    ctx = _build_context(
        config=config,
        soc_pct=soc_pct,
        capacity_kwh=capacity_kwh,
        kwh_remaining=kwh_remaining,
        forecast_rows=forecast_rows,
        live_load_kw=live_load_kw,
        horizon_hours=horizon_hours,
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

    plan_slot = _current_plan_slot(daily_plan)
    eval_tier = "daily_plan" if plan_slot else "tactical"
    if plan_slot and plan_slot.get("action") == "charge":
        pass  # fall through to grid charge evaluator

    return evaluate_grid_charge(
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
