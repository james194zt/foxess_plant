"""Pure helpers to pick the cheapest import half-hour (most negative preferred)."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def pick_best_import_slot(
    slots: list[Any],
    *,
    current: datetime,
    horizon: datetime,
    require_negative: bool = False,
    max_import_p: float | None = None,
) -> Any | None:
    """Lowest import_p in [current, horizon); ties prefer the earlier slot.

    Example: -0.04p at 02:00 vs -0.05p at 03:00 → wait for -0.05p.
    """
    best: Any | None = None
    best_p = 999999.0
    for slot in slots:
        if slot.end <= current or slot.start >= horizon:
            continue
        import_p = slot.import_p_per_kwh
        if import_p is None:
            continue
        if require_negative and import_p >= 0:
            continue
        if max_import_p is not None and import_p > max_import_p:
            continue
        if import_p < best_p or (
            best is not None and import_p == best_p and slot.start < best.start
        ):
            best_p = import_p
            best = slot
    return best


def trough_import_price(
    slots: list[Any],
    *,
    require_negative: bool = False,
    max_import_p: float | None = None,
) -> float | None:
    """Minimum import price among eligible slots (or None)."""
    trough: float | None = None
    for slot in slots:
        import_p = slot.import_p_per_kwh
        if import_p is None:
            continue
        if require_negative and import_p >= 0:
            continue
        if max_import_p is not None and import_p > max_import_p:
            continue
        if trough is None or import_p < trough:
            trough = import_p
    return trough
