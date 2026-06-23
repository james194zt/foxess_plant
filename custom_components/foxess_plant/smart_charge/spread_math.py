"""Pure spread math — no Home Assistant dependency (unit-testable)."""

from __future__ import annotations

OPERATING_MODE_MAX_GREEN = "max_green"
OPERATING_MODE_MAX_PROFIT = "max_profit"


def spread_profit_per_kwh(
    *,
    import_p_per_kwh: float,
    export_p_per_kwh: float,
    round_trip_efficiency: float,
) -> float:
    """Estimated arbitrage profit (p/kWh) for buy import then sell export."""
    eff = max(0.1, min(1.0, round_trip_efficiency))
    return (export_p_per_kwh + eff * abs(min(0.0, import_p_per_kwh))) - max(0.0, import_p_per_kwh)


def is_peak_import_hour(local_hour: int, *, start_hour: int = 16, end_hour: int = 19) -> bool:
    return start_hour <= local_hour < end_hour


def greener_night_for_local_date(greener_nights: list[dict], local_date_iso: str) -> bool:
    for row in greener_nights:
        if str(row.get("date")) == local_date_iso and row.get("is_greener_night"):
            return True
    return False


def mode_spread_threshold(
    operating_mode: str,
    *,
    min_spread_profit: float,
    green_export_spread_multiplier: float,
) -> float:
    if operating_mode == OPERATING_MODE_MAX_GREEN:
        return min_spread_profit * max(1.0, green_export_spread_multiplier)
    if operating_mode == OPERATING_MODE_MAX_PROFIT:
        return min_spread_profit
    return min_spread_profit * 1.25


def score_charge_slot(
    *,
    import_p_per_kwh: float,
    carbon_score: int | None,
    is_greener: bool,
    operating_mode: str,
    green_carbon_weight: float,
    peak_penalty_p: float,
    is_peak: bool,
) -> float:
    """Lower is better for charge attractiveness (negative import scores best)."""
    score = import_p_per_kwh
    if is_peak:
        score += peak_penalty_p
    if operating_mode == OPERATING_MODE_MAX_GREEN:
        weight = max(0.0, min(1.0, green_carbon_weight))
        if is_greener:
            score -= 3.0 * weight
        if carbon_score is not None:
            score -= (carbon_score - 5) * 0.5 * weight
    return score


def pair_spread_indices(
    charge_scores: list[tuple[int, float]],
    export_scores: list[tuple[int, float, float]],
    *,
    min_profit_p: float,
) -> list[tuple[int, int, float]]:
    """Greedy non-overlapping charge→export pairs by spread profit."""
    candidates: list[tuple[int, int, float]] = []
    for ci, import_p in charge_scores:
        for ei, export_p, profit in export_scores:
            if ei <= ci:
                continue
            if profit < min_profit_p:
                continue
            candidates.append((ci, ei, profit))
    candidates.sort(key=lambda row: -row[2])
    used: set[int] = set()
    selected: list[tuple[int, int, float]] = []
    for ci, ei, profit in candidates:
        overlap = any(idx in used for idx in range(ci, ei + 1))
        if overlap:
            continue
        selected.append((ci, ei, profit))
        used.update(range(ci, ei + 1))
    return selected


def winter_fill_slot_count(
    *,
    grid_gap_kwh: float,
    forecast_kwh: float,
    solar_margin: float,
    slot_kwh: float = 0.5,
) -> int:
    margin = max(1.0, solar_margin)
    shortfall = max(0.0, grid_gap_kwh - (forecast_kwh or 0.0) / margin)
    if shortfall <= 0 or slot_kwh <= 0:
        return 0
    return max(1, int(round(shortfall / slot_kwh)))


def rates_snapshot(import_rates: list[dict]) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for row in import_rates:
        try:
            out.append((str(row.get("valid_from")), float(row.get("value_inc_vat"))))
        except (TypeError, ValueError):
            continue
    return out


def material_import_price_drop(
    previous: list[tuple[str, float]],
    current: list[tuple[str, float]],
    *,
    threshold_p: float,
) -> bool:
    if not previous or not current:
        return False
    prev_map = {k: v for k, v in previous}
    for key, new_p in current:
        old_p = prev_map.get(key)
        if old_p is None:
            continue
        if old_p - new_p >= threshold_p:
            return True
    return False
