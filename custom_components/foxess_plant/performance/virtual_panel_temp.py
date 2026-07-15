"""Virtual panel temperature from string voltage (Ideas doc 4).

This is a *relative* estimate: it only works when baseline string voltage is
calibrated at the same operating point used live (typically near-MPP under
good sun). Comparing open-circuit Voc baseline to loaded Vmp, or using an
unconfigured 400 V default on a different plant, produces nonsense temps.

Guards reject weak irradiance, voltage far from baseline, clamp hits, and
(when ambient is available) physically impossible panel rise.
"""

from __future__ import annotations

# Need enough irradiance that the string is near MPP, not dawdling dawn power.
MIN_PV_KW_FOR_TEMP = 0.5
MIN_PV_FRACTION_OF_AC = 0.12

# Live voltage must be within this band of the calibrated baseline.
MAX_VOLTAGE_DELTA_BELOW = 0.12  # 12% below baseline
MAX_VOLTAGE_DELTA_ABOVE = 0.08  # 8% above baseline

TEMP_CLAMP_MIN_C = -10.0
TEMP_CLAMP_MAX_C = 85.0

# Typical crystalline modules: max ΔT panel−air ~25–40°C in peak sun.
MAX_PANEL_RISE_ABOVE_AMBIENT_C = 40.0
MIN_PANEL_BELOW_AMBIENT_C = 5.0


def compute_virtual_panel_temp_c(
    *,
    string_voltage_v: float | None,
    pv_power_kw: float | None,
    baseline_v_at_25c: float,
    temp_coefficient_v_per_c: float = -0.003,
    inverter_ac_limit_kw: float | None = None,
    ambient_temp_c: float | None = None,
) -> float | None:
    """Estimate panel temperature from Voc/Vmp shift vs STC baseline at 25°C."""
    if string_voltage_v is None or pv_power_kw is None:
        return None

    min_kw = MIN_PV_KW_FOR_TEMP
    if inverter_ac_limit_kw is not None and inverter_ac_limit_kw > 0:
        min_kw = max(min_kw, float(inverter_ac_limit_kw) * MIN_PV_FRACTION_OF_AC)
    if float(pv_power_kw) < min_kw:
        return None

    baseline = float(baseline_v_at_25c)
    coeff = float(temp_coefficient_v_per_c)
    if baseline <= 0 or coeff == 0:
        return None

    live_v = float(string_voltage_v)
    if live_v <= 0:
        return None

    voltage_delta_pct = (live_v - baseline) / baseline
    # Far from calibration voltage ⇒ baseline wrong or not comparable (Vmp vs Voc).
    if voltage_delta_pct < -MAX_VOLTAGE_DELTA_BELOW or voltage_delta_pct > MAX_VOLTAGE_DELTA_ABOVE:
        return None

    # coeff is fraction per °C (e.g. -0.003 = -0.3%/°C).
    temp_delta_c = voltage_delta_pct / coeff
    temp_c = 25.0 + temp_delta_c

    # Hitting the clamp means the estimate already ran off the rails — don't publish it.
    if temp_c <= TEMP_CLAMP_MIN_C or temp_c >= TEMP_CLAMP_MAX_C:
        return None

    if ambient_temp_c is not None:
        ambient = float(ambient_temp_c)
        if temp_c > ambient + MAX_PANEL_RISE_ABOVE_AMBIENT_C:
            return None
        if temp_c < ambient - MIN_PANEL_BELOW_AMBIENT_C:
            return None

    return round(temp_c, 1)
