"""Derive Solcast PV forecast sensor values from hobbyist detailed_forecast rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .solcast_pv import _parse_dt

# Default window for "Forecast next X hours" (matches common Solcast card setups).
FORECAST_NEXT_X_HOURS = 3

# Flattened keys consumed by FoxessPlantSolcastForecastSensor (and solcast_status_dict).
FORECAST_METRIC_KEYS: frozenset[str] = frozenset(
    {
        "forecast_today_kwh",
        "forecast_tomorrow_kwh",
        "forecast_remaining_today_kwh",
        "forecast_this_hour_wh",
        "forecast_next_hour_wh",
        "forecast_next_x_hours_kwh",
        "peak_forecast_today_w",
        "peak_forecast_tomorrow_w",
        "peak_time_today",
        "peak_time_tomorrow",
        "power_now_w",
        "power_in_30_minutes_w",
        "power_in_1_hour_w",
    }
)


@dataclass(frozen=True)
class _Interval:
    start: datetime
    end: datetime
    kw: float
    kwh: float


def _period_hours(rows: list[dict[str, Any]], index: int, default: float = 0.5) -> float:
    if index + 1 < len(rows):
        t0 = _parse_dt(rows[index].get("period_start"))
        t1 = _parse_dt(rows[index + 1].get("period_start"))
        if t0 and t1:
            return max(0.083, (t1 - t0).total_seconds() / 3600.0)
    return default


def _build_intervals(rows: list[dict[str, Any]]) -> list[_Interval]:
    ordered = sorted(
        (r for r in rows if _parse_dt(r.get("period_start")) is not None),
        key=lambda r: str(r.get("period_start")),
    )
    intervals: list[_Interval] = []
    for i, row in enumerate(ordered):
        start = _parse_dt(row.get("period_start"))
        if start is None:
            continue
        try:
            kw = float(row["pv_estimate"])
        except (KeyError, TypeError, ValueError):
            continue
        hours = _period_hours(ordered, i)
        end = start + timedelta(hours=hours)
        if i + 1 < len(ordered):
            next_start = _parse_dt(ordered[i + 1].get("period_start"))
            if next_start and next_start > start:
                end = next_start
        intervals.append(_Interval(start=start, end=end, kw=kw, kwh=kw * hours))
    return intervals


def _local_date(when: datetime) -> date:
    return dt_util.as_local(when).date()


def _hour_bounds_local(when: datetime) -> tuple[datetime, datetime]:
    local = dt_util.as_local(when)
    start = local.replace(minute=0, second=0, microsecond=0)
    return start, start + timedelta(hours=1)


def _overlap_kwh(interval: _Interval, window_start: datetime, window_end: datetime) -> float:
    """Energy in kWh for the portion of an interval inside [window_start, window_end)."""
    seg_start = max(interval.start, window_start)
    seg_end = min(interval.end, window_end)
    if seg_end <= seg_start:
        return 0.0
    duration_h = (seg_end - seg_start).total_seconds() / 3600.0
    total_h = (interval.end - interval.start).total_seconds() / 3600.0
    if total_h <= 0:
        return 0.0
    return interval.kwh * (duration_h / total_h)


def _power_w_at(intervals: list[_Interval], when: datetime) -> float | None:
    for iv in intervals:
        if iv.start <= when < iv.end:
            return round(iv.kw * 1000.0, 1)
    future = [iv for iv in intervals if iv.start >= when]
    if future:
        return round(future[0].kw * 1000.0, 1)
    if intervals:
        return round(intervals[-1].kw * 1000.0, 1)
    return None


def _sum_kwh(
    intervals: list[_Interval],
    *,
    day: date | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> float:
    total = 0.0
    for iv in intervals:
        if day is not None and _local_date(iv.start) != day:
            continue
        if after is not None and iv.end <= after:
            continue
        if before is not None and iv.start >= before:
            continue
        if window_start is not None and window_end is not None:
            total += _overlap_kwh(iv, window_start, window_end)
        else:
            total += iv.kwh
    return total


def _peak_today(intervals: list[_Interval], day: date) -> tuple[float | None, datetime | None]:
    peak_kw = -1.0
    peak_at: datetime | None = None
    for iv in intervals:
        if _local_date(iv.start) != day:
            continue
        if iv.kw > peak_kw:
            peak_kw = iv.kw
            peak_at = iv.start
    if peak_at is None:
        return None, None
    return round(peak_kw * 1000.0, 1), peak_at


def compute_forecast_metrics(
    hass: HomeAssistant | None,
    rows: list[dict[str, Any]],
    *,
    next_hours: int = FORECAST_NEXT_X_HOURS,
) -> dict[str, Any]:
    """Build sensor-ready values aligned with ha-solcast-solar entity semantics."""
    del hass  # timezone via dt_util (HA configured locale)
    if not rows:
        return {}
    now = dt_util.now()
    today = _local_date(now)
    tomorrow = today + timedelta(days=1)
    intervals = _build_intervals(rows)
    if not intervals:
        return {}

    hour_start, hour_end = _hour_bounds_local(now)
    next_hour_start = hour_end
    next_hour_end = next_hour_start + timedelta(hours=1)
    next_x_end = now + timedelta(hours=max(1, next_hours))
    hour_start_utc = dt_util.as_utc(hour_start)
    hour_end_utc = dt_util.as_utc(hour_end)
    next_hour_start_utc = dt_util.as_utc(next_hour_start)
    next_hour_end_utc = dt_util.as_utc(next_hour_end)

    forecast_today = _sum_kwh(intervals, day=today)
    forecast_tomorrow = _sum_kwh(intervals, day=tomorrow)
    forecast_remaining = _sum_kwh(intervals, day=today, after=now)
    this_hour_wh = (
        _sum_kwh(intervals, window_start=hour_start_utc, window_end=hour_end_utc) * 1000.0
    )
    next_hour_wh = (
        _sum_kwh(
            intervals,
            window_start=next_hour_start_utc,
            window_end=next_hour_end_utc,
        )
        * 1000.0
    )
    next_x_kwh = _sum_kwh(intervals, after=now, before=next_x_end)

    peak_today_w, peak_time_today = _peak_today(intervals, today)
    peak_tomorrow_w, peak_time_tomorrow = _peak_today(intervals, tomorrow)

    power_now_w = _power_w_at(intervals, now)
    power_30_w = _power_w_at(intervals, now + timedelta(minutes=30))
    power_1h_w = _power_w_at(intervals, now + timedelta(hours=1))

    detailed_ha = [
        {
            "period_start": iv.start.isoformat(),
            "period_end": iv.end.isoformat(),
            "pv_estimate": round(iv.kw, 4),
        }
        for iv in intervals
    ]

    return {
        "forecast_today_kwh": round(forecast_today, 2),
        "forecast_tomorrow_kwh": round(forecast_tomorrow, 2),
        "forecast_remaining_today_kwh": round(forecast_remaining, 2),
        "forecast_this_hour_wh": round(this_hour_wh, 0),
        "forecast_next_hour_wh": round(next_hour_wh, 0),
        "forecast_next_x_hours_kwh": round(next_x_kwh, 2),
        "forecast_next_x_hours": next_hours,
        "peak_forecast_today_w": peak_today_w,
        "peak_forecast_tomorrow_w": peak_tomorrow_w,
        "peak_time_today": peak_time_today,
        "peak_time_tomorrow": peak_time_tomorrow,
        "power_now_w": power_now_w,
        "power_in_30_minutes_w": power_30_w,
        "power_in_1_hour_w": power_1h_w,
        "detailed_forecast_ha": detailed_ha,
    }


def strip_volatile_forecast_metrics(parsed: dict[str, Any]) -> dict[str, Any]:
    """Drop time-sensitive flattened metrics before persisting (recomputed on load)."""
    out = dict(parsed)
    for key in FORECAST_METRIC_KEYS | {
        "forecast_metrics",
        "detailed_forecast_ha",
        "power_now_kw",
        "energy_remaining_kwh",
        "forecast_next_x_hours",
    }:
        out.pop(key, None)
    return out


def apply_forecast_metrics(
    parsed: dict[str, Any] | None,
    hass: HomeAssistant | None = None,
) -> dict[str, Any]:
    """Merge sensor-ready metrics into pv_forecast_parsed from detailed_forecast rows."""
    if not isinstance(parsed, dict):
        return {}
    rows = parsed.get("detailed_forecast")
    if not isinstance(rows, list) or not rows:
        return dict(parsed)
    out = dict(parsed)
    metrics = compute_forecast_metrics(hass, rows)
    if not metrics:
        for key in FORECAST_METRIC_KEYS:
            out.pop(key, None)
        out.pop("forecast_metrics", None)
        out.pop("detailed_forecast_ha", None)
        return out
    out["forecast_metrics"] = metrics
    for key, value in metrics.items():
        if key != "detailed_forecast_ha":
            out[key] = value
    if metrics.get("power_now_w") is not None:
        out["power_now_kw"] = metrics["power_now_w"] / 1000.0
    if metrics.get("forecast_remaining_today_kwh") is not None:
        out["energy_remaining_kwh"] = metrics["forecast_remaining_today_kwh"]
    out["period_count"] = len(rows)
    return out


def merge_forecast_metrics_into_status(
    target: dict[str, Any],
    parsed: dict[str, Any] | None,
    hass: HomeAssistant | None,
) -> None:
    """Copy forecast rows and flattened sensor metrics onto a solcast status dict."""
    if not isinstance(parsed, dict):
        target["pv_forecast_available"] = False
        target.setdefault("detailed_forecast", [])
        return
    enriched = apply_forecast_metrics(parsed, hass)
    rows = enriched.get("detailed_forecast")
    if not isinstance(rows, list):
        rows = []
    target["pv_forecast_available"] = len(rows) >= 1
    target["detailed_forecast"] = rows
    target["detailed_forecast_by_site"] = enriched.get("detailed_forecast_by_site") or {}
    target["pv_power_now_kw"] = enriched.get("power_now_kw")
    target["pv_energy_remaining_kwh"] = enriched.get("energy_remaining_kwh")
    target["pv_forecast_periods"] = enriched.get("period_count", 0)
    for key in FORECAST_METRIC_KEYS:
        if key in enriched:
            target[key] = enriched[key]
    if "forecast_next_x_hours" in enriched:
        target["forecast_next_x_hours"] = enriched["forecast_next_x_hours"]
