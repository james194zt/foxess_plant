"""Environmental impact estimates (Fox Cloud / FoxESS app style)."""

from __future__ import annotations

from typing import Any

# Fox Forest / Impact (reverse-engineered vs FoxCloud app + foxess_modbus):
# - Trees and oil: lifetime Yield Total (total_yield_total).
# - CO₂: lifetime solar self-consumption (solar_energy_total − feed_in_energy_total),
#   which Fox shows ~0.8 kg below yield at ~260 kWh (e.g. 259.8 vs 260.6).
# When solar/export totals are missing or inconsistent with yield, fall back to the
# same ~0.31% offset Fox applies below yield.
OIL_LITRES_PER_YIELD_KWH = 0.123
# Empirical Fox offset below yield (~0.8 kg per 260 kWh); used only as fallback.
FOX_CO2_YIELD_OFFSET_RATIO = 0.00307
# Self-consumed solar must be within this of yield or we distrust feed_in mapping.
FOX_CO2_YIELD_MAX_DELTA_KWH = 2.0

PV_TOTAL_KEYS = tuple(f"pv{i}_energy_total" for i in range(1, 7))


def _float_state(states: dict[str, str | None], key: str) -> float:
    raw = states.get(key)
    if raw in (None, "unknown", "unavailable", ""):
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def lifetime_yield_kwh(entity_states: dict[str, str | None]) -> float:
    """Lifetime yield (kWh) — FoxCloud trees/oil basis (total_yield_total)."""
    total = _float_state(entity_states, "total_yield_total")
    if total > 0:
        return total
    total = _float_state(entity_states, "solar_energy_total")
    if total > 0:
        return total
    return sum(_float_state(entity_states, key) for key in PV_TOTAL_KEYS)


def lifetime_solar_kwh(entity_states: dict[str, str | None]) -> float:
    """Total lifetime PV generation (kWh)."""
    total = _float_state(entity_states, "solar_energy_total")
    if total > 0:
        return total
    return sum(_float_state(entity_states, key) for key in PV_TOTAL_KEYS)


def lifetime_co2_kwh(entity_states: dict[str, str | None], yield_kwh: float) -> float:
    """Lifetime kWh basis for Fox CO₂ (self-consumed solar, validated against yield)."""
    solar = lifetime_solar_kwh(entity_states)
    export = _float_state(entity_states, "feed_in_energy_total")
    if solar > export > 0:
        self_consumed = solar - export
        if self_consumed > 0 and abs(self_consumed - yield_kwh) <= max(
            FOX_CO2_YIELD_MAX_DELTA_KWH, yield_kwh * 0.015
        ):
            return self_consumed
    return yield_kwh * (1.0 - FOX_CO2_YIELD_OFFSET_RATIO)


def compute_impact(entity_states: dict[str, str | None]) -> dict[str, Any]:
    """Estimate CO₂, oil, and trees to match FoxCloud Impact."""
    yield_kwh = lifetime_yield_kwh(entity_states)
    if yield_kwh <= 0:
        return {}
    co2_kwh = lifetime_co2_kwh(entity_states, yield_kwh)
    co2_kg = co2_kwh
    oil_l = yield_kwh * OIL_LITRES_PER_YIELD_KWH
    trees = yield_kwh
    return {
        "yield_kwh_total": round(yield_kwh, 1),
        "co2_basis_kwh": round(co2_kwh, 1),
        "impact_basis_kwh": round(yield_kwh, 1),
        "co2_kg": round(co2_kg, 1),
        "oil_litres": round(oil_l, 1),
        "trees_planted": round(trees, 1),
    }
