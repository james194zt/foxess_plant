"""Virtual panel temperature from string voltage (Ideas doc 4)."""

from __future__ import annotations

MIN_PV_KW_FOR_TEMP = 0.1
TEMP_CLAMP_MIN_C = -10.0
TEMP_CLAMP_MAX_C = 85.0


def compute_virtual_panel_temp_c(
    *,
    string_voltage_v: float | None,
    pv_power_kw: float | None,
    baseline_v_at_25c: float,
    temp_coefficient_v_per_c: float = -0.003,
) -> float | None:
    """Estimate panel temperature from Voc/Vmp shift vs STC baseline at 25°C."""
    if string_voltage_v is None or pv_power_kw is None:
        return None
    if pv_power_kw < MIN_PV_KW_FOR_TEMP:
        return None
    baseline = float(baseline_v_at_25c)
    coeff = float(temp_coefficient_v_per_c)
    if baseline <= 0 or coeff == 0:
        return None
    voltage_delta_pct = (float(string_voltage_v) - baseline) / baseline
    temp_delta_c = voltage_delta_pct / coeff
    temp_c = 25.0 + temp_delta_c
    return round(max(TEMP_CLAMP_MIN_C, min(TEMP_CLAMP_MAX_C, temp_c)), 1)
