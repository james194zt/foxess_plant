"""Solcast forecast helpers for SmartCharge."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from ..solcast_forecast_metrics import compute_forecast_metrics
from ..solcast_pv import _parse_dt


def solcast_remaining_kwh(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    metrics = compute_forecast_metrics(None, rows)
    value = metrics.get("forecast_remaining_today_kwh")
    return float(value) if value is not None else None


def solcast_forecast_kwh_for_horizon(
    rows: list[dict[str, Any]],
    *,
    horizon_hours: float = 24.0,
) -> float | None:
    if not rows:
        return None
    now = dt_util.now()
    end = now + timedelta(hours=max(0.5, horizon_hours))
    total = 0.0
    found = False
    ordered = sorted(
        (r for r in rows if _parse_dt(r.get("period_start")) is not None),
        key=lambda r: str(r.get("period_start")),
    )
    for i, row in enumerate(ordered):
        start = _parse_dt(row.get("period_start"))
        if start is None or start >= end:
            continue
        if start < now and i + 1 < len(ordered):
            next_start = _parse_dt(ordered[i + 1].get("period_start"))
            if next_start and next_start <= now:
                continue
        try:
            kw = float(row["pv_estimate"])
        except (KeyError, TypeError, ValueError):
            continue
        if i + 1 < len(ordered):
            next_start = _parse_dt(ordered[i + 1].get("period_start"))
            if next_start and next_start > start:
                seg_end = min(next_start, end)
            else:
                seg_end = min(start + timedelta(minutes=30), end)
        else:
            seg_end = min(start + timedelta(minutes=30), end)
        seg_start = max(start, now)
        if seg_end <= seg_start:
            continue
        hours = (seg_end - seg_start).total_seconds() / 3600.0
        total += kw * hours
        found = True
    return round(total, 2) if found else None
