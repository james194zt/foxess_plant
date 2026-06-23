"""Smart charge — combine Solcast forecast with tariff rates for grid charging."""

from __future__ import annotations

from .grid_charge import (
    battery_deficit_kwh,
    evaluate_grid_charge,
    find_negative_import_slot,
    rate_slots_from_octopus,
    rate_slots_from_schedule,
)
from .reserve import (
    OPERATING_MODE_MAX_GREEN,
    OPERATING_MODE_MAX_PROFIT,
    OPERATING_MODE_MAX_SAFETY,
    OPERATING_MODES,
    compute_exportable_kwh,
    compute_min_reserve_soc,
    compute_outage_reserve_kwh,
)
from .solcast_budget import HouseEnergyBudget, compute_house_energy_budget
from .solcast_remaining import solcast_forecast_kwh_for_horizon, solcast_remaining_kwh
from .strategy import build_daily_plan, evaluate_smart_charge
from .types import RateSlot, SmartChargeDecision, charge_periods_signature

__all__ = [
    "OPERATING_MODE_MAX_GREEN",
    "OPERATING_MODE_MAX_PROFIT",
    "OPERATING_MODE_MAX_SAFETY",
    "OPERATING_MODES",
    "HouseEnergyBudget",
    "RateSlot",
    "SmartChargeDecision",
    "battery_deficit_kwh",
    "build_daily_plan",
    "charge_periods_signature",
    "compute_exportable_kwh",
    "compute_house_energy_budget",
    "compute_min_reserve_soc",
    "compute_outage_reserve_kwh",
    "evaluate_grid_charge",
    "evaluate_smart_charge",
    "find_negative_import_slot",
    "rate_slots_from_octopus",
    "rate_slots_from_schedule",
    "solcast_forecast_kwh_for_horizon",
    "solcast_remaining_kwh",
]
