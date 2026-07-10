"""Inverter AC clipping loss estimation."""

from __future__ import annotations

CLIPPING_THRESHOLD = 0.98


def compute_clipping_loss_kw(
    *,
    pv_power_kw: float | None,
    inverter_ac_limit_kw: float,
    recent_peak_kw: float | None = None,
) -> float:
    """Estimated kW lost to inverter AC saturation (0 when not clipping)."""
    if pv_power_kw is None or inverter_ac_limit_kw <= 0:
        return 0.0
    limit = float(inverter_ac_limit_kw)
    pv = max(0.0, float(pv_power_kw))
    threshold = limit * CLIPPING_THRESHOLD
    if pv < threshold:
        return 0.0
    if recent_peak_kw is not None and recent_peak_kw > pv:
        theoretical = float(recent_peak_kw)
    else:
        theoretical = pv * 1.05
    loss = max(0.0, theoretical - limit)
    return round(min(loss, theoretical), 3)
