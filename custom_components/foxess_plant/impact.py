"""Environmental impact estimates (Fox Cloud / FoxESS app style)."""

from __future__ import annotations

from typing import Any

# Fox Forest / Impact (reverse-engineered from FoxCloud app vs inverter totals):
# - Basis: lifetime PV generation (solar_energy_total), not self-consumption.
# - CO₂ kg ≈ kWh × 1.0; trees ≈ same numeric scale; oil L ≈ kWh × 0.123.
CO2_KG_PER_KWH = 1.0
OIL_LITRES_PER_KWH = 0.123
TREES_PER_KWH = 1.0

PV_TOTAL_KEYS = tuple(f"pv{i}_energy_total" for i in range(1, 7))


def _float_state(states: dict[str, str | None], key: str) -> float:
    raw = states.get(key)
    if raw in (None, "unknown", "unavailable", ""):
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def lifetime_solar_kwh(entity_states: dict[str, str | None]) -> float:
    """Total lifetime PV generation (kWh) from inverter total or sum of MPPT totals."""
    total = _float_state(entity_states, "solar_energy_total")
    if total > 0:
        return total
    return sum(_float_state(entity_states, key) for key in PV_TOTAL_KEYS)


def lifetime_self_consumed_kwh(entity_states: dict[str, str | None]) -> float:
    """Lifetime PV used on-site (Fox self-consumption): generation minus export."""
    generated = lifetime_solar_kwh(entity_states)
    if generated <= 0:
        return 0.0
    exported = _float_state(entity_states, "feed_in_energy_total")
    return max(0.0, generated - exported)


def compute_impact(entity_states: dict[str, str | None]) -> dict[str, Any]:
    """Estimate CO₂, oil, and trees from lifetime PV generation (Fox Forest style)."""
    generated = lifetime_solar_kwh(entity_states)
    exported = _float_state(entity_states, "feed_in_energy_total")
    self_consumed = lifetime_self_consumed_kwh(entity_states)
    kwh = generated
    if kwh <= 0:
        return {}
    co2_kg = kwh * CO2_KG_PER_KWH
    oil_l = kwh * OIL_LITRES_PER_KWH
    trees = kwh * TREES_PER_KWH
    return {
        "solar_kwh_total": round(generated, 1),
        "export_kwh_total": round(exported, 1),
        "self_consumption_kwh_total": round(self_consumed, 1),
        "impact_basis_kwh": round(kwh, 1),
        "co2_kg": round(co2_kg, 1),
        "oil_litres": round(oil_l, 1),
        "trees_planted": round(trees, 1),
    }
