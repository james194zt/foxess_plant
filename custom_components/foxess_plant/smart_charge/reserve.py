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


def compute_exportable_kwh(
    *,
    kwh_remaining: float | None,
    reserve_kwh: float,
    capacity_kwh: float | None = None,
    export_min_soc: float | None = None,
    soc_pct: float | None = None,
) -> float | None:
    """Energy above the higher of outage reserve and virtual export-floor SOC."""
    if kwh_remaining is None:
        return None
    floor_kwh = max(0.0, float(reserve_kwh or 0.0))
    if (
        capacity_kwh is not None
        and capacity_kwh > 0
        and export_min_soc is not None
    ):
        floor_kwh = max(floor_kwh, capacity_kwh * max(0.0, float(export_min_soc)) / 100.0)
    if soc_pct is not None and export_min_soc is not None and float(soc_pct) <= float(export_min_soc):
        return 0.0
    return max(0.0, float(kwh_remaining) - floor_kwh)


def compute_min_reserve_soc(*, reserve_kwh: float, capacity_kwh: float | None) -> float | None:
    if capacity_kwh is None or capacity_kwh <= 0:
        return None
    return min(100.0, max(0.0, reserve_kwh / capacity_kwh * 100.0))


def export_floor_reached(*, soc_pct: float | None, export_min_soc: float | None) -> bool:
    """True when live SOC is at/below the virtual export floor."""
    if soc_pct is None or export_min_soc is None:
        return False
    return float(soc_pct) <= float(export_min_soc)
