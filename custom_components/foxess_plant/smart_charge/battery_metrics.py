"""Resolve battery SOC, capacity, and remaining energy for SmartCharge."""

from __future__ import annotations

from typing import Any, Callable


def parse_state_float(raw: Any) -> float | None:
    """Parse HA entity state to float (handles trailing % and commas)."""
    if raw in (None, "unavailable", "unknown", ""):
        return None
    text = str(raw).strip().replace(",", ".")
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def design_energy_wh_to_kwh(value: float, unit: str) -> float:
    """Convert BMS design-energy reading to kWh."""
    unit_l = (unit or "").strip().lower()
    if unit_l == "kwh":
        return value
    if unit_l == "wh":
        return value / 1000.0
    return value / 1000.0 if value > 200 else value


def resolve_battery_metrics(
    *,
    read_float: Callable[[str], float | None],
    read_unit: Callable[[str], str],
) -> tuple[float | None, float | None, float | None]:
    """Return (soc_pct, capacity_kwh, kwh_remaining) using layered fallbacks."""
    soc_pct = read_float("battery_soc")

    capacity_kwh = _capacity_kwh(read_float, read_unit)
    kwh_remaining = _kwh_remaining(read_float, read_unit, soc_pct, capacity_kwh)

    if (capacity_kwh is None or capacity_kwh <= 0) and soc_pct is not None and soc_pct > 0:
        if kwh_remaining is not None and kwh_remaining > 0:
            capacity_kwh = kwh_remaining * 100.0 / soc_pct

    if (kwh_remaining is None or kwh_remaining < 0) and soc_pct is not None and capacity_kwh is not None:
        if capacity_kwh > 0:
            kwh_remaining = capacity_kwh * soc_pct / 100.0

    if capacity_kwh is not None and capacity_kwh <= 0:
        capacity_kwh = None
    if kwh_remaining is not None and kwh_remaining < 0:
        kwh_remaining = None

    return soc_pct, capacity_kwh, kwh_remaining


def _capacity_kwh(
    read_float: Callable[[str], float | None],
    read_unit: Callable[[str], str],
) -> float | None:
    nominal = read_float("bms_kwh_nominal")
    if nominal is not None and nominal > 0:
        return nominal

    # EVO names nominal pack energy bms_kwh_remaining_1 (register 37632).
    evo_nominal = read_float("bms_kwh_remaining_1")
    if evo_nominal is not None and evo_nominal > 0:
        return evo_nominal

    design = read_float("bms_design_energy_wh")
    if design is not None and design > 0:
        return design_energy_wh_to_kwh(design, read_unit("bms_design_energy_wh"))

    voltage = _battery_voltage_v(read_float)
    if voltage is not None:
        for key in ("bms_ah_nominal", "bms_ah_fcc"):
            ah = read_float(key)
            if ah is not None and ah > 0:
                return ah * voltage / 1000.0

    return None


def _kwh_remaining(
    read_float: Callable[[str], float | None],
    read_unit: Callable[[str], str],
    soc_pct: float | None,
    capacity_kwh: float | None,
) -> float | None:
    remaining = read_float("battery_kwh_remaining")
    if remaining is not None and remaining >= 0:
        return remaining

    voltage = _battery_voltage_v(read_float)
    if voltage is not None:
        for key in ("battery_ah_remaining", "bms_ah_remaining"):
            ah = read_float(key)
            if ah is not None and ah >= 0:
                return ah * voltage / 1000.0

    if soc_pct is not None and capacity_kwh is not None and capacity_kwh > 0:
        return capacity_kwh * soc_pct / 100.0

    return None


def _battery_voltage_v(read_float: Callable[[str], float | None]) -> float | None:
    for key in ("batvolt_1", "invbatvolt_1", "battery_voltage"):
        volts = read_float(key)
        if volts is not None and volts > 10:
            return volts
    return None


__all__ = [
    "design_energy_wh_to_kwh",
    "parse_state_float",
    "resolve_battery_metrics",
]
