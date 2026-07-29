"""Pure helpers to pick the highest export half-hour above a threshold."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def pick_best_export_slot(
    slots: list[Any],
    *,
    min_export_p: float,
    current: datetime,
    horizon: datetime,
) -> Any | None:
    """Highest export_p in [current, horizon); ties prefer the earlier slot."""
    best: Any | None = None
    best_p = -999.0
    for slot in slots:
        if slot.end <= current or slot.start >= horizon:
            continue
        export_p = slot.export_p_per_kwh
        if export_p is None or export_p < min_export_p:
            continue
        if export_p > best_p or (
            best is not None and export_p == best_p and slot.start < best.start
        ):
            best_p = export_p
            best = slot
    return best


def peak_export_price(
    slots: list[Any],
    *,
    min_export_p: float,
) -> float | None:
    """Max export price among slots that clear the threshold (or None)."""
    peak: float | None = None
    for slot in slots:
        export_p = slot.export_p_per_kwh
        if export_p is None or export_p < min_export_p:
            continue
        if peak is None or export_p > peak:
            peak = export_p
    return peak
