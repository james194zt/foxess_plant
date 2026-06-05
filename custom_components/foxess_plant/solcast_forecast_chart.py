"""Rebuild today's PV forecast chart from persisted Solcast poll snapshots."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .solcast_forecast_metrics import _build_intervals
from .solcast_store import _snapshot_has_forecast

STATISTICS_PERIOD_MS = 5 * 60 * 1000


def _parse_fetched_at_ms(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value if value > 1e12 else value * 1000)
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        n = float(text)
        return n if n > 1e12 else n * 1000
    parsed = dt_util.parse_datetime(text)
    if parsed is None:
        return None
    return dt_util.as_utc(parsed).timestamp() * 1000


def _detailed_rows(cache: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(cache, dict):
        return []
    parsed = cache.get("pv_forecast_parsed")
    if not isinstance(parsed, dict):
        return []
    rows = parsed.get("detailed_forecast")
    return rows if isinstance(rows, list) else []


def _kw_at_time(rows: list[dict[str, Any]], when) -> float | None:
    for interval in _build_intervals(rows):
        if interval.start <= when < interval.end:
            return interval.kw
    return None


def _snapshot_for_time(
    snapshots: list[tuple[float, list[dict[str, Any]]]],
    slot_ms: float,
) -> list[dict[str, Any]] | None:
    chosen: list[dict[str, Any]] | None = None
    for fetched_ms, rows in snapshots:
        if fetched_ms <= slot_ms:
            chosen = rows
    return chosen


def build_forecast_intraday_chart(
    hass: HomeAssistant,
    stored: dict[str, Any] | None,
    current_cache: dict[str, Any] | None,
) -> list[dict[str, float]]:
    """Chart points for today: past slots use the forecast known at that time."""
    now = dt_util.now()
    day_start = dt_util.start_of_local_day(now)
    day_start_ms = day_start.timestamp() * 1000
    now_ms = now.timestamp() * 1000
    t_max_ms = day_start_ms + 24 * 60 * 60 * 1000

    snapshots: list[tuple[float, list[dict[str, Any]]]] = []
    history = stored.get("history") if isinstance(stored, dict) else None
    if isinstance(history, list):
        for item in history:
            if not isinstance(item, dict):
                continue
            cache = item.get("cache")
            if not _snapshot_has_forecast(cache):
                continue
            fetched_ms = _parse_fetched_at_ms(item.get("fetched_at"))
            if fetched_ms is None:
                fetched_ms = _parse_fetched_at_ms(
                    (cache or {}).get("updated_at") or (cache or {}).get("pv_forecast_fetched_at")
                )
            if fetched_ms is None or fetched_ms < day_start_ms - 3_600_000:
                continue
            rows = _detailed_rows(cache)
            if len(rows) >= 2:
                snapshots.append((fetched_ms, rows))

    if _snapshot_has_forecast(current_cache):
        fetched_ms = _parse_fetched_at_ms(
            (current_cache or {}).get("updated_at")
            or (current_cache or {}).get("pv_forecast_fetched_at")
        )
        rows = _detailed_rows(current_cache)
        if fetched_ms is not None and len(rows) >= 2:
            if not snapshots or abs(snapshots[-1][0] - fetched_ms) > 1000:
                snapshots.append((fetched_ms, rows))

    snapshots.sort(key=lambda item: item[0])
    if not snapshots:
        return []

    latest_rows = snapshots[-1][1]
    out: list[dict[str, float]] = []
    slot = int(day_start_ms)
    while slot <= t_max_ms:
        when = dt_util.utc_from_timestamp(slot / 1000)
        if slot <= now_ms:
            rows = _snapshot_for_time(snapshots, slot)
        else:
            rows = latest_rows
        if rows:
            kw = _kw_at_time(rows, when)
            if kw is not None:
                out.append({"t": float(slot), "v": float(kw)})
        slot += STATISTICS_PERIOD_MS
    return out
