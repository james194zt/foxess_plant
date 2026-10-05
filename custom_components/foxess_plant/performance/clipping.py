"""Inverter AC clipping loss.

Clipping is power the panels could have made but couldn't be used: the inverter's AC output was at its limit and
the battery wasn't taking the rest (full, or at its Max SoC). While the battery soaks up the surplus nothing is lost,
even though PV is above the AC limit. It needs an estimate of what the panels could make (Solcast's for the array);
without one, or when the inverter isn't at its limit, the loss is 0.
"""

from __future__ import annotations

AT_LIMIT_FRACTION = 0.97  # AC output within 3 % of the limit counts as "at the limit"
BATTERY_TAKING_KW = 0.2  # battery charging faster than this is still absorbing the surplus


def compute_clipping_loss_kw(
    *,
    pv_power_kw: float | None,
    inverter_ac_limit_kw: float,
    potential_kw: float | None = None,
    ac_output_kw: float | None = None,
    battery_charge_kw: float | None = None,
) -> float:
    """kW lost: Solcast's potential above the actual PV while the AC side is at its limit and the battery is full.

    Without an AC output reading, PV is compared with the limit instead (a system with no battery).
    """
    if pv_power_kw is None or potential_kw is None or inverter_ac_limit_kw <= 0:
        return 0.0
    pv = max(0.0, float(pv_power_kw))
    at_limit = abs(float(ac_output_kw)) if ac_output_kw is not None else pv
    if at_limit < float(inverter_ac_limit_kw) * AT_LIMIT_FRACTION:
        return 0.0
    if battery_charge_kw is not None and float(battery_charge_kw) > BATTERY_TAKING_KW:
        return 0.0
    return round(max(0.0, float(potential_kw) - pv), 3)
