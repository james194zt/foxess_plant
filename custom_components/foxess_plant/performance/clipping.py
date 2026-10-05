"""Inverter AC clipping loss.

Clipping is power the panels could have made but the inverter couldn't pass on because it was at its AC limit.
It needs an estimate of what the panels could make: Solcast's estimate for the array. Without one, or when the
inverter isn't at its limit, the loss is 0. (A system whose panels can't exceed the inverter's rating never clips.)
"""

from __future__ import annotations

AT_LIMIT_FRACTION = 0.97  # output within 3 % of the AC limit counts as "at the limit"


def compute_clipping_loss_kw(
    *,
    pv_power_kw: float | None,
    inverter_ac_limit_kw: float,
    potential_kw: float | None = None,
) -> float:
    """kW lost to the inverter's AC limit: Solcast's potential above the actual output while at the limit."""
    if pv_power_kw is None or potential_kw is None or inverter_ac_limit_kw <= 0:
        return 0.0
    pv = max(0.0, float(pv_power_kw))
    if pv < float(inverter_ac_limit_kw) * AT_LIMIT_FRACTION:
        return 0.0
    return round(max(0.0, float(potential_kw) - pv), 3)
