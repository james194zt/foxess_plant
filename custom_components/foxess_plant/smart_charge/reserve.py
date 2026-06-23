"""Outage reserve floor — minimum battery energy during vulnerable windows."""

from __future__ import annotations

OPERATING_MODE_MAX_PROFIT = "max_profit"
OPERATING_MODE_MAX_SAFETY = "max_safety"
OPERATING_MODE_MAX_GREEN = "max_green"
OPERATING_MODES = (
    OPERATING_MODE_MAX_PROFIT,
    OPERATING_MODE_MAX_SAFETY,
    OPERATING_MODE_MAX_GREEN,
)


def mode_reserve_multiplier(operating_mode: str, *, safety_reserve_multiplier: float) -> float:
    if operating_mode == OPERATING_MODE_MAX_SAFETY:
        return max(1.0, safety_reserve_multiplier)
    if operating_mode == OPERATING_MODE_MAX_GREEN:
        return 1.1
    return 1.0


def compute_outage_reserve_kwh(
    *,
    avg_home_load_kw: float,
    vulnerable_hours: float,
    safety_margin: float,
    operating_mode: str = OPERATING_MODE_MAX_SAFETY,
    safety_reserve_multiplier: float = 1.5,
) -> float:
    load_kw = max(0.0, avg_home_load_kw)
    hours = max(0.0, vulnerable_hours)
    margin = max(1.0, safety_margin)
    mode_mult = mode_reserve_multiplier(
        operating_mode, safety_reserve_multiplier=safety_reserve_multiplier
    )
    return load_kw * hours * margin * mode_mult


def compute_exportable_kwh(*, kwh_remaining: float | None, reserve_kwh: float) -> float | None:
    if kwh_remaining is None:
        return None
    return max(0.0, kwh_remaining - max(0.0, reserve_kwh))


def compute_min_reserve_soc(*, reserve_kwh: float, capacity_kwh: float | None) -> float | None:
    if capacity_kwh is None or capacity_kwh <= 0:
        return None
    return min(100.0, max(0.0, reserve_kwh / capacity_kwh * 100.0))
