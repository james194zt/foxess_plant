"""Spread optimizer — paired charge/discharge across Agile half-hour slots."""

from __future__ import annotations

from typing import Any

from homeassistant.util import dt as dt_util

from .carbon_slots import carbon_for_instant, greener_night_active
from .context import config_float
from .export_limits import export_allowed_for_mode, mode_export_limits
from .export_peak import planned_export_kwh, solcast_covers_export_recharge
from .grid_charge import _fmt_hhmm, _merge_slots
from .solcast_remaining import solcast_forecast_kwh_for_horizon
from .spread_math import (
    OPERATING_MODE_MAX_GREEN,
    is_peak_import_hour,
    mode_spread_threshold,
    pair_spread_indices,
    score_charge_slot,
    spread_profit_per_kwh,
    winter_fill_slot_count,
)
from .types import RateSlot


def _peak_hours(config: Any) -> tuple[int, int]:
    start_s = str(getattr(config, "peak_import_avoid_start", "16:00") or "16:00")
    end_s = str(getattr(config, "peak_import_avoid_end", "19:00") or "19:00")
    try:
        return int(start_s.split(":")[0]), int(end_s.split(":")[0])
    except (TypeError, ValueError, IndexError):
        return 16, 19


def _slot_is_peak(slot: RateSlot, config: Any) -> bool:
    start_h, end_h = _peak_hours(config)
    local = dt_util.as_local(slot.start)
    return is_peak_import_hour(local.hour, start_hour=start_h, end_hour=end_h)


def optimize_spread_plan(
    *,
    config: Any,
    slots: list[RateSlot],
    ctx: dict[str, Any],
    forecast_rows: list[dict[str, Any]],
    horizon_hours: float,
    carbon_periods: list[dict[str, Any]] | None = None,
    greener_nights: list[dict[str, Any]] | None = None,
    exportable_kwh: float | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (plan entries, spread_pairs metadata)."""
    carbon_periods = carbon_periods or []
    greener_nights = greener_nights or []
    operating_mode = ctx["operating_mode"]
    round_trip = config_float(config, "round_trip_efficiency", 0.9)
    margin = config_float(config, "solar_safety_margin", 1.15)
    min_spread = config_float(config, "min_spread_profit_p_per_kwh", 3.0)
    green_mult = config_float(config, "green_export_spread_multiplier", 2.0)
    green_weight = config_float(config, "green_carbon_weight", 0.5)
    peak_penalty = config_float(config, "peak_import_penalty_p_per_kwh", 5.0)
    cheap_import_p = config_float(config, "cheap_import_p_per_kwh", 8.0)
    threshold = mode_spread_threshold(
        operating_mode,
        min_spread_profit=min_spread,
        green_export_spread_multiplier=green_mult,
    )
    min_export_p, _ = mode_export_limits(operating_mode, config)
    allow_export = export_allowed_for_mode(operating_mode, config)
    exportable = exportable_kwh if exportable_kwh is not None else ctx.get("exportable_kwh")

    merged = _merge_slots(slots)
    plan: list[dict[str, Any]] = []
    for slot in merged:
        export_p = slot.export_p_per_kwh
        carbon = carbon_for_instant(slot.start, carbon_periods)
        carbon_score = carbon.get("low_carbon_score") if carbon else None
        greener = greener_night_active(slot.start, greener_nights)
        plan.append(
            {
                "start": _fmt_hhmm(slot.start),
                "end": _fmt_hhmm(slot.end),
                "import_p_per_kwh": round(slot.import_p_per_kwh, 4),
                "export_p_per_kwh": round(export_p, 4) if export_p is not None else None,
                "carbon_score": carbon_score,
                "is_greener_night": greener,
                "action": "idle",
                "reason": "hold",
            }
        )

    charge_scores: list[tuple[int, float]] = []
    export_scores: list[tuple[int, float, float]] = []
    for i, slot in enumerate(merged):
        entry = plan[i]
        import_p = slot.import_p_per_kwh
        export_p = slot.export_p_per_kwh or 0.0
        is_peak = _slot_is_peak(slot, config)
        if import_p < 0 or import_p <= cheap_import_p:
            charge_scores.append(
                (
                    i,
                    score_charge_slot(
                        import_p_per_kwh=import_p,
                        carbon_score=entry.get("carbon_score"),
                        is_greener=bool(entry.get("is_greener_night")),
                        operating_mode=operating_mode,
                        green_carbon_weight=green_weight,
                        peak_penalty_p=peak_penalty,
                        is_peak=is_peak,
                    ),
                )
            )
        if allow_export and export_p >= min_export_p:
            profit = spread_profit_per_kwh(
                import_p_per_kwh=import_p,
                export_p_per_kwh=export_p,
                round_trip_efficiency=round_trip,
            )
            export_scores.append((i, export_p, profit))

    pairs_meta: list[dict[str, Any]] = []
    from ..octopus_tariff import is_tracker_tariff_type

    spread_enabled = bool(getattr(config, "spread_optimizer_enabled", True))
    if spread_enabled and not is_tracker_tariff_type(ctx.get("tariff_type")):
        charge_sorted = sorted(charge_scores, key=lambda row: row[1])
        raw_pairs = pair_spread_indices(charge_sorted, export_scores, min_profit_p=threshold)
        for ci, ei, profit in raw_pairs:
            charge_entry = plan[ci]
            export_entry = plan[ei]
            export_slot = merged[ei]
            export_kwh = planned_export_kwh(
                exportable_kwh=exportable,
                slot=export_slot,
                operating_mode=operating_mode,
                config=config,
            )
            if operating_mode == OPERATING_MODE_MAX_GREEN and profit < threshold * 1.5:
                continue
            if export_kwh and not solcast_covers_export_recharge(
                forecast_rows,
                export_kwh=export_kwh,
                solar_safety_margin=margin,
                horizon_hours=horizon_hours,
            ):
                continue
            charge_entry["action"] = "spread_charge"
            charge_entry["reason"] = "spread_pair"
            charge_entry["pair_export_start"] = export_entry["start"]
            charge_entry["expected_spread_p_per_kwh"] = round(profit, 2)
            export_entry["action"] = "spread_export"
            export_entry["reason"] = "spread_pair"
            export_entry["pair_charge_start"] = charge_entry["start"]
            export_entry["expected_spread_p_per_kwh"] = round(profit, 2)
            if export_kwh:
                export_entry["planned_export_kwh"] = export_kwh
            pairs_meta.append(
                {
                    "charge_start": charge_entry["start"],
                    "export_start": export_entry["start"],
                    "spread_p_per_kwh": round(profit, 2),
                }
            )

    for i, slot in enumerate(merged):
        entry = plan[i]
        if entry["action"] != "idle":
            continue
        import_p = slot.import_p_per_kwh
        export_p = slot.export_p_per_kwh
        if import_p < 0:
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
            elif import_p <= cheap_import_p and not _slot_is_peak(slot, config):
                entry["action"] = "charge_candidate"
                entry["reason"] = "cheap_import"
        elif import_p <= cheap_import_p and not _slot_is_peak(slot, config):
            entry["action"] = "charge_candidate"
            entry["reason"] = "cheap_import"

    if bool(getattr(config, "winter_fill_enabled", True)):
        forecast_kwh = solcast_forecast_kwh_for_horizon(forecast_rows, horizon_hours=horizon_hours) or 0.0
        fill_count = winter_fill_slot_count(
            grid_gap_kwh=float(ctx.get("grid_gap_kwh") or 0.0),
            forecast_kwh=forecast_kwh,
            solar_margin=margin,
        )
        if fill_count > 0:
            candidates = [
                (i, plan[i], merged[i])
                for i in range(len(plan))
                if plan[i]["action"] in ("idle", "charge_candidate")
                and not _slot_is_peak(merged[i], config)
            ]
            candidates.sort(key=lambda row: row[2].import_p_per_kwh)
            for i, entry, _slot in candidates[:fill_count]:
                entry["action"] = "charge"
                entry["reason"] = "solar_gap_fill"
                entry["solar_gap_fill"] = True

    return plan, pairs_meta
