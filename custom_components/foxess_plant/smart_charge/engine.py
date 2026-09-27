"""SmartCharge engine — Home Assistant glue around the pure planner."""

from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
from typing import Any

from homeassistant.util import dt as dt_util

from . import planner
from .load_profile import average_load_kw
from .reserve import compute_outage_reserve_kwh
from .types import SmartChargeDecision
from .windows import periods_for_window

REPLAN_MAX_AGE = timedelta(minutes=60)
REPLAN_SOC_DRIFT_PCT = 10.0


def local_tz() -> tzinfo:
    getter = getattr(dt_util, "get_default_time_zone", None)
    return getter() if callable(getter) else dt_util.DEFAULT_TIME_ZONE


def forecast_signature(rows: list[dict[str, Any]] | None) -> str:
    if not rows:
        return ""
    starts = sorted(str(r.get("period_start")) for r in rows)
    total = sum(float(r.get("pv_estimate") or 0) for r in rows)
    return f"{len(rows)}|{starts[0]}|{starts[-1]}|{total:.2f}"


def compute_plan(
    *,
    config: Any,
    now: datetime,
    import_rows: list[dict[str, Any]],
    export_rows: list[dict[str, Any]] | None,
    forecast_rows: list[dict[str, Any]] | None,
    load_profile: dict[str, Any] | None,
    carbon_periods: list[dict[str, Any]] | None,
    soc_pct: float | None,
    capacity_kwh: float | None,
    kwh_remaining: float | None,
    inverter_min_soc_pct: float | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build and optimise the plan. CPU-bound — call from an executor."""
    if not capacity_kwh or capacity_kwh <= 0:
        return [], {"error": "Battery capacity unavailable"}
    if kwh_remaining is None and soc_pct is None:
        return [], {"error": "Battery SOC unavailable"}
    if not import_rows:
        return [], {"error": "No import rate timeline available"}

    tz = local_tz()
    mode = str(getattr(config, "operating_mode", planner.MODE_MAX_SAFETY) or planner.MODE_MAX_SAFETY)
    fallback_kw = float(getattr(config, "house_load_kw_fallback", 1.0) or 1.0)
    avg_kw = average_load_kw(load_profile, fallback_kw)
    reserve_load = getattr(config, "outage_reserve_load_kw", None)
    reserve_kwh = compute_outage_reserve_kwh(
        avg_home_load_kw=float(reserve_load) if reserve_load is not None else avg_kw,
        vulnerable_hours=float(getattr(config, "outage_reserve_hours", 3.0) or 0.0),
        safety_margin=float(getattr(config, "outage_reserve_margin", 1.2) or 1.0),
        operating_mode=mode,
        safety_reserve_multiplier=float(getattr(config, "safety_reserve_multiplier", 1.5) or 1.0),
    )
    params = planner.params_from_config(
        config,
        capacity_kwh=float(capacity_kwh),
        reserve_kwh=reserve_kwh,
        inverter_min_soc_pct=inverter_min_soc_pct,
    )
    soc_kwh = (
        float(kwh_remaining)
        if kwh_remaining is not None
        else float(capacity_kwh) * float(soc_pct) / 100.0
    )
    slots = planner.build_timeline(
        now=now,
        tz=tz,
        import_rows=import_rows,
        export_rows=export_rows,
        forecast_rows=forecast_rows,
        load_profile=load_profile,
        load_fallback_kw=fallback_kw,
        carbon_periods=carbon_periods,
    )
    plan, summary = planner.build_plan(slots, soc_kwh, params, tz=tz, now=now)
    cap = float(capacity_kwh)
    meta = {
        **summary.to_dict(),
        "built_at": now.isoformat(),
        "operating_mode": mode,
        "reserve_kwh": round(reserve_kwh, 2),
        "floor_pct": round(params.floor_kwh / cap * 100.0, 1),
        "export_floor_pct": round(params.export_floor_kwh / cap * 100.0, 1),
        "cap_pct": round(params.cap_kwh / cap * 100.0, 1),
        "charge_kw": params.charge_kw,
        "discharge_kw": params.discharge_kw,
        "export_allowed": params.export_allowed,
        "load_source": "history" if load_profile else "fallback",
        "load_history_days": (load_profile or {}).get("days"),
        "avg_load_kw": round(avg_kw, 2),
        "horizon_end": plan[-1]["end_utc"] if plan else None,
        "unknown_price_slots": sum(1 for e in plan if not e.get("price_known")),
        "soc_start_pct": round(soc_kwh / cap * 100.0, 1),
    }
    return plan, meta


def replan_reason(
    *,
    plan: list[dict[str, Any]],
    meta: dict[str, Any],
    now: datetime,
    rates_sig: str,
    forecast_sig: str,
    soc_pct: float | None,
) -> str | None:
    """Why the committed plan must be rebuilt (None = keep it)."""
    if not plan or not meta:
        return "no_plan"
    built = planner.parse_iso(meta.get("built_at"))
    if built is None or now - built >= REPLAN_MAX_AGE:
        return "hourly"
    if planner.plan_index_at(plan, now) is None:
        return "plan_expired"
    if meta.get("rates_sig") != rates_sig:
        return "rates_changed"
    if meta.get("forecast_sig") != forecast_sig:
        return "forecast_changed"
    expected = planner.expected_soc_pct(plan, now)
    if soc_pct is not None and expected is not None and abs(soc_pct - expected) > REPLAN_SOC_DRIFT_PCT:
        return "soc_drift"
    return None


def decision_from_plan(
    *,
    config: Any,
    plan: list[dict[str, Any]],
    meta: dict[str, Any],
    now: datetime,
    soc_pct: float | None,
) -> SmartChargeDecision:
    mode = meta.get("operating_mode") or getattr(config, "operating_mode", None)
    common = {
        "operating_mode": mode,
        "reserve_kwh": meta.get("reserve_kwh"),
        "grid_gap_kwh": meta.get("grid_charge_kwh"),
        "forecast_kwh": meta.get("tomorrow_pv_kwh"),
        "daily_plan": plan,
        "eval_tier": "plan",
        "plan_summary": meta,
    }
    if meta.get("error"):
        return SmartChargeDecision(action="idle", reason=str(meta["error"]), **common)

    d = planner.decide(plan, now)
    common["next_charge"] = d.get("next_charge")
    common["next_export"] = d.get("next_export")
    window = d.get("window")
    action = d["action"]
    target = d.get("target_soc_pct")

    if action in ("grid_charge", "arbitrage") and window:
        return SmartChargeDecision(
            action=action,
            reason=d["reason"],
            charge_periods=periods_for_window(window, list(getattr(config, "charge_periods", []) or [])),
            target_max_soc=target,
            target_soc_effective=target,
            windows=[window],
            **common,
        )
    if action == "export_discharge" and window:
        end_soc = window.get("soc_end_pct")
        if soc_pct is not None and end_soc is not None and soc_pct <= float(end_soc) - 1.0:
            return SmartChargeDecision(
                action="idle",
                reason=f"Planned export done (SOC {soc_pct:.0f}% ≤ {float(end_soc):.0f}%)",
                work_mode_target="Self Use",
                **common,
            )
        return SmartChargeDecision(
            action="export_discharge",
            reason=d["reason"],
            windows=[window],
            discharge_window=window,
            planned_export_kwh=window.get("kwh"),
            target_soc_effective=end_soc,
            work_mode_target="Force Discharge",
            **common,
        )
    return SmartChargeDecision(action="idle", reason=d["reason"], **common)
