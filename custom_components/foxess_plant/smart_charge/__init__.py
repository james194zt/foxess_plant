"""SmartCharge — cost-optimised grid charge / export planning from tariff, Solcast and load."""

from __future__ import annotations

from .guards import smart_charge_evaluation_blocked
from .planner import current_plan_slot
from .reserve import (
    OPERATING_MODE_MAX_GREEN,
    OPERATING_MODE_MAX_PROFIT,
    OPERATING_MODE_MAX_SAFETY,
    OPERATING_MODES,
    battery_deficit_kwh,
    compute_exportable_kwh,
    compute_min_reserve_soc,
    compute_outage_reserve_kwh,
)
from .types import SmartChargeDecision, charge_periods_signature, discharge_window_signature
from .windows import charge_periods_active_now, discharge_window_active_now

__all__ = [
    "OPERATING_MODE_MAX_GREEN",
    "OPERATING_MODE_MAX_PROFIT",
    "OPERATING_MODE_MAX_SAFETY",
    "OPERATING_MODES",
    "SmartChargeDecision",
    "battery_deficit_kwh",
    "charge_periods_active_now",
    "charge_periods_signature",
    "compute_exportable_kwh",
    "compute_min_reserve_soc",
    "compute_outage_reserve_kwh",
    "current_plan_slot",
    "discharge_window_active_now",
    "discharge_window_signature",
    "smart_charge_evaluation_blocked",
]
