"""Panel (cell) temperature from the panel datasheet, the weather and the array's output.

Model: the manufacturer's NOCT formula, extended for wind (Faiman) and mounting.

  NOCT (datasheet): cell temperature at 800 W/m² sun, 20 °C air, 1 m/s wind, open rack, so
      Tcell = Tair + (NOCT - 20) / 800 × G                      (the standard datasheet formula)
  Faiman form:  Tcell = Tair + G / (U0 + U1 × wind)
      U1 = 6.84 W/m²K per m/s (pvlib default) and U0 chosen so that at 1 m/s it gives exactly the NOCT formula.
  Mounting: panels with less air behind them shed heat less well. The heat-loss factor is scaled by PVsyst's
      standard ratios: open rack 29, on-roof with an air gap ("semi-integrated") 20, in-roof 15 W/m²K.

Sunlight on the panels (G, W/m²) comes from the array's DC output: G = 1000 × P / (P_stc × (1 + γ (Tcell - 25))),
which itself depends on the temperature, so the two are solved together.
"""

from __future__ import annotations

from dataclasses import dataclass

FAIMAN_U1 = 6.84
MOUNTING_FACTORS = {"open_rack": 1.0, "roof_gap": 20.0 / 29.0, "in_roof": 15.0 / 29.0}
NOCT_WIND_MS = 1.0
MAX_IRRADIANCE = 1400.0  # W/m²: above this the output figures are wrong, not the sun


@dataclass(frozen=True)
class ArrayThermal:
    """The datasheet / installation values the model needs for one array."""

    stc_kw: float  # DC output at STC after the array's efficiency factor
    noct_c: float = 45.0
    power_temp_coeff_pct: float = -0.30
    mounting: str = "roof_gap"


def heat_loss_w_per_m2k(array: ArrayThermal, wind_ms: float | None) -> float:
    """How much power per m² per °C the panels shed (Faiman U, scaled for mounting)."""
    u0 = max(5.0, 800.0 / max(1.0, array.noct_c - 20.0) - FAIMAN_U1)
    wind = NOCT_WIND_MS if wind_ms is None else max(0.0, float(wind_ms))
    return MOUNTING_FACTORS.get(array.mounting, MOUNTING_FACTORS["roof_gap"]) * (u0 + FAIMAN_U1 * wind)


def cell_temp_c(array: ArrayThermal, *, air_c: float, irradiance_w_m2: float, wind_ms: float | None) -> float:
    return air_c + max(0.0, irradiance_w_m2) / heat_loss_w_per_m2k(array, wind_ms)


def irradiance_and_temp(
    array: ArrayThermal, *, dc_kw: float, air_c: float, wind_ms: float | None
) -> tuple[float, float] | None:
    """(sunlight on the panels W/m², cell temperature °C) from the array's DC output; None if not usable."""
    if array.stc_kw <= 0 or dc_kw is None or dc_kw < 0:
        return None
    gamma = array.power_temp_coeff_pct / 100.0
    temp = air_c
    irradiance = 0.0
    for _ in range(4):  # converges in 2-3 steps
        derate = max(0.5, 1.0 + gamma * (temp - 25.0))
        irradiance = 1000.0 * dc_kw / (array.stc_kw * derate)
        temp = cell_temp_c(array, air_c=air_c, irradiance_w_m2=irradiance, wind_ms=wind_ms)
    if irradiance > MAX_IRRADIANCE:
        return None
    return round(irradiance, 1), round(temp, 1)


def plant_panel_temp_c(
    arrays: list[tuple[ArrayThermal, float]], *, air_c: float | None, wind_ms: float | None
) -> float | None:
    """Output-weighted panel temperature across arrays [(array, DC kW)], or None without air temperature or sun."""
    if air_c is None:
        return None
    weighted = 0.0
    total = 0.0
    for array, dc_kw in arrays:
        result = irradiance_and_temp(array, dc_kw=dc_kw, air_c=air_c, wind_ms=wind_ms)
        if result is None:
            continue
        weight = max(array.stc_kw, 0.01)
        weighted += result[1] * weight
        total += weight
    return round(weighted / total, 1) if total else None


def still_air_temp_c(
    arrays: list[tuple[ArrayThermal, float]], *, air_c: float | None
) -> float | None:
    """The same, with no wind: the difference to the real figure is how much the wind is cooling the panels."""
    return plant_panel_temp_c(arrays, air_c=air_c, wind_ms=0.0)
