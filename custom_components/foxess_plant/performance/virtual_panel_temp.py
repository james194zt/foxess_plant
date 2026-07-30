"""Virtual panel temperature from string voltage (Ideas doc 4).

This is a *relative* estimate: it only works when baseline string voltage is
calibrated at the same operating point used live (typically near-MPP under
good sun). Comparing open-circuit Voc baseline to loaded Vmp, or using an
unconfigured 400 V default on a different plant, produces nonsense temps.

Guards reject weak irradiance, voltage far from baseline, clamp hits, and
(when ambient is available) physically impossible panel rise.

When the configured baseline is clearly wrong for the live string, callers
can seed a replacement via `suggest_baseline_v_at_25c`.
"""

from __future__ import annotations

# Need enough irradiance that the string is near MPP, not dawdling dawn power.
# Keep this an absolute floor (matches the Performance chart hint). Do not scale by
# inverter AC rating — 12% of a 10 kW EVO (~1.2 kW) blanks the chart all morning.
MIN_PV_KW_FOR_TEMP = 0.5

# Live voltage must be within this band of the calibrated baseline.
MAX_VOLTAGE_DELTA_BELOW = 0.12  # 12% below baseline
MAX_VOLTAGE_DELTA_ABOVE = 0.08  # 8% above baseline

TEMP_CLAMP_MIN_C = -10.0
TEMP_CLAMP_MAX_C = 85.0

# Typical crystalline modules: max ΔT panel−air ~25–40°C in peak sun.
MAX_PANEL_RISE_ABOVE_AMBIENT_C = 40.0
MIN_PANEL_BELOW_AMBIENT_C = 5.0

FACTORY_BASELINE_V = 400.0
BASELINE_SEED_MIN_V = 200.0
BASELINE_SEED_MAX_V = 600.0


def voltage_out_of_baseline_band(*, live_v: float, baseline_v: float) -> bool:
    if baseline_v <= 0 or live_v <= 0:
        return True
    delta_pct = (live_v - baseline_v) / baseline_v
    return delta_pct < -MAX_VOLTAGE_DELTA_BELOW or delta_pct > MAX_VOLTAGE_DELTA_ABOVE


def suggest_baseline_v_at_25c(
    *,
    string_voltage_v: float,
    ambient_temp_c: float | None,
    pv_power_kw: float,
    inverter_ac_limit_kw: float | None = None,
    temp_coefficient_v_per_c: float = -0.003,
) -> float | None:
    """Infer V@25°C assuming panels sit at ambient + irradiance-scaled rise.

    Used to recover from a factory/wrong baseline that would otherwise leave
    the estimate permanently empty.
    """
    live_v = float(string_voltage_v)
    if live_v <= 50:
        return None

    ac = float(inverter_ac_limit_kw) if inverter_ac_limit_kw and inverter_ac_limit_kw > 0 else 4.3
    frac = min(1.0, max(0.0, float(pv_power_kw) / max(ac, 0.1)))
    ambient = float(ambient_temp_c) if ambient_temp_c is not None else 20.0
    # ~8°C rise at low useful power → ~30°C at full AC (NOCT-ish scaling).
    assumed_panel_c = ambient + (8.0 + 22.0 * frac)
    coeff = float(temp_coefficient_v_per_c)
    factor = 1.0 + coeff * (assumed_panel_c - 25.0)
    if factor <= 0.2:
        return None
    baseline = live_v / factor
    if baseline < BASELINE_SEED_MIN_V or baseline > BASELINE_SEED_MAX_V:
        return None
    return round(baseline, 1)


def compute_virtual_panel_temp_c(
    *,
    string_voltage_v: float | None,
    pv_power_kw: float | None,
    baseline_v_at_25c: float,
    temp_coefficient_v_per_c: float = -0.003,
    inverter_ac_limit_kw: float | None = None,
    ambient_temp_c: float | None = None,
) -> float | None:
    """Estimate panel temperature from Voc/Vmp shift vs STC baseline at 25°C.

    ``inverter_ac_limit_kw`` is accepted for API compatibility but no longer raises
    the minimum PV gate (see ``MIN_PV_KW_FOR_TEMP``).
    """
    _ = inverter_ac_limit_kw
    if string_voltage_v is None or pv_power_kw is None:
        return None

    min_kw = MIN_PV_KW_FOR_TEMP
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
