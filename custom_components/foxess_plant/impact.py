"""Environmental impact estimates (Fox Cloud / FoxESS app style)."""

from __future__ import annotations

from typing import Any

# Fox Forest / Impact (reverse-engineered vs FoxCloud app + foxess_modbus Yield Total):
# - Trees and oil: lifetime Yield Total (total_yield_total) × 1.0 / × 0.123.
# - CO₂: same yield × ~0.99693 (Fox shows ~0.8 kg less than trees at ~260 kWh).
#   e.g. yield 260.6 → trees 260.6, CO₂ 259.8, oil 32.1 L.
FOX_CO2_YIELD_RATIO = 259.8 / 260.6
OIL_LITRES_PER_YIELD_KWH = 0.123
TREES_PER_YIELD_KWH = 1.0

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
    """Lifetime yield (kWh) — FoxCloud Impact basis (foxess_modbus total_yield_total)."""
    total = _float_state(entity_states, "total_yield_total")
    if total > 0:
        return total
    total = _float_state(entity_states, "solar_energy_total")
    if total > 0:
        return total
    return sum(_float_state(entity_states, key) for key in PV_TOTAL_KEYS)


def compute_impact(entity_states: dict[str, str | None]) -> dict[str, Any]:
    """Estimate CO₂, oil, and trees from lifetime yield (Fox Forest / Yield Total)."""
    yield_kwh = lifetime_yield_kwh(entity_states)
    if yield_kwh <= 0:
        return {}
    co2_kg = yield_kwh * FOX_CO2_YIELD_RATIO
    oil_l = yield_kwh * OIL_LITRES_PER_YIELD_KWH
    trees = yield_kwh * TREES_PER_YIELD_KWH
    return {
        "yield_kwh_total": round(yield_kwh, 1),
        "impact_basis_kwh": round(yield_kwh, 1),
        "co2_basis_kwh": round(yield_kwh * FOX_CO2_YIELD_RATIO, 1),
        "co2_kg": round(co2_kg, 1),
        "oil_litres": round(oil_l, 1),
        "trees_planted": round(trees, 1),
    }
