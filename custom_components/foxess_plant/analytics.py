"""Daily energy analytics derived from mapped inverter entities."""

from __future__ import annotations

from typing import Any


def _float_state(states: dict[str, str | None], key: str) -> float:
    raw = states.get(key)
    if raw in (None, "unknown", "unavailable", ""):
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def compute_analytics(entity_states: dict[str, str | None]) -> dict[str, Any]:
    """Mirror Solar Analysis calculations from the Fox-style dashboard."""
    pv = _float_state(entity_states, "solar_energy_today")
    to_grid = _float_state(entity_states, "feed_in_energy_today")
    # Export (feed-in) cannot exceed PV generation for the same period.
    if pv > 0:
        to_grid = min(to_grid, pv)
    to_load_battery = max(0.0, pv - to_grid)

    base_load = _float_state(entity_states, "load_energy_today")
    battery_discharge = _float_state(entity_states, "battery_discharge_today")
    battery_charge = _float_state(entity_states, "battery_charge_today")
    from_grid = _float_state(entity_states, "grid_consumption_energy_today")
    load_consumption = base_load - battery_discharge + battery_charge + from_grid
    from_pv_battery = max(0.0, load_consumption - from_grid)

    self_consumption = min(100.0, max(0.0, (to_load_battery / pv) * 100)) if pv > 0 else 0.0
    self_sufficiency = (
        min(100.0, max(0.0, (from_pv_battery / load_consumption) * 100))
        if load_consumption > 0
        else 0.0
    )

    return {
        "pv_production_kwh_today": round(pv, 2),
        "pv_to_load_battery_kwh_today": round(to_load_battery, 2),
        "pv_to_grid_kwh_today": round(to_grid, 2),
        "load_consumption_kwh_today": round(load_consumption, 2),
        "load_from_pv_battery_kwh_today": round(from_pv_battery, 2),
        "load_from_grid_kwh_today": round(from_grid, 2),
        "self_consumption_percent_today": round(self_consumption, 1),
        "self_sufficiency_percent_today": round(self_sufficiency, 1),
        # Panel expects these balance keys (aliases for balance card).
        "battery_charge_kwh_today": round(battery_charge, 2),
        "battery_discharge_kwh_today": round(battery_discharge, 2),
    }
