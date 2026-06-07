"""Rebuild PV forecast chart lines from persisted polls and recorder history."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .solcast_forecast_metrics import _build_intervals
from .solcast_store import _snapshot_has_forecast, get_daily_intraday_points

STATISTICS_PERIOD_MS = 5 * 60 * 1000
# Include polls from the previous evening when rebuilding a local day chart.
SNAPSHOT_GRACE_MS = 24 * 3_600_000


def _utc_from_timestamp(ts: float) -> datetime:
    """UTC datetime from epoch seconds (HA removed dt_util.utc_from_timestamp)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc)


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


def _detailed_rows_from_attrs(attrs: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(attrs, dict):
        return []
    rows = attrs.get("detailed_forecast") or attrs.get("detailedForecast")
    return rows if isinstance(rows, list) and len(rows) >= 2 else []


def _kw_at_time(rows: list[dict[str, Any]], when: datetime) -> float | None:
    for interval in _build_intervals(rows):
        if interval.start <= when < interval.end:
            return interval.kw
    return None


def _kw_at_or_after(rows: list[dict[str, Any]], when: datetime) -> float | None:
    """Latest forecast kW at or before *when*, else first interval kW (future slots)."""
    intervals = _build_intervals(rows)
    if not intervals:
        return None
    chosen: float | None = None
    for interval in intervals:
        if interval.start <= when:
            chosen = interval.kw
        elif chosen is None:
            return interval.kw
        else:
            break
    return chosen if chosen is not None else intervals[-1].kw


def _snapshot_for_time(
    snapshots: list[tuple[float, list[dict[str, Any]]]],
    slot_ms: float,
) -> list[dict[str, Any]] | None:
    chosen: list[dict[str, Any]] | None = None
    for fetched_ms, rows in snapshots:
        if fetched_ms <= slot_ms:
            chosen = rows
    return chosen


def _merge_snapshots(
    *groups: list[tuple[float, list[dict[str, Any]]]],
) -> list[tuple[float, list[dict[str, Any]]]]:
    merged: dict[float, list[dict[str, Any]]] = {}
    for group in groups:
        for fetched_ms, rows in group:
            if len(rows) >= 2:
                merged[float(fetched_ms)] = rows
    return sorted(merged.items(), key=lambda item: item[0])


def collect_storage_snapshots(
    stored: dict[str, Any] | None,
    current_cache: dict[str, Any] | None,
    day_start_ms: float,
) -> list[tuple[float, list[dict[str, Any]]]]:
    """Poll snapshots from HA .storage (survives reboot) relevant to this local day."""
    snapshots: list[tuple[float, list[dict[str, Any]]]] = []
    cutoff_ms = day_start_ms - SNAPSHOT_GRACE_MS
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
            if fetched_ms is None or fetched_ms < cutoff_ms:
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

    return sorted(snapshots, key=lambda item: item[0])


def find_solcast_forecast_entity(hass: HomeAssistant, entry_id: str) -> str | None:
    """Fox Plant Solcast sensor that carries detailed_forecast attributes."""
    reg = er.async_get(hass)
    target_uid = f"{entry_id}_solcast_forecast_today"
    for entity in reg.entities.values():
        if entity.unique_id == target_uid:
            return entity.entity_id
    for entity in reg.entities.values():
        if entity.config_entry_id != entry_id:
            continue
        if entity.unique_id.endswith("_solcast_forecast_today"):
            return entity.entity_id
    return None


def collect_recorder_snapshots(
    hass: HomeAssistant,
    entity_id: str,
    day_start: datetime,
    day_end: datetime,
) -> list[tuple[float, list[dict[str, Any]]]]:
    """Forecast poll snapshots from HA recorder state history (attribute changes)."""
    from homeassistant.components.recorder import history
    from homeassistant.components.recorder.util import session_scope

    snapshots: list[tuple[float, list[dict[str, Any]]]] = []
    start_utc = dt_util.as_utc(day_start)
    end_utc = dt_util.as_utc(day_end)
    with session_scope(hass=hass, read_only=True) as session:
        states_map = history.get_significant_states_with_session(
            hass,
            session,
            start_utc - timedelta(hours=1),
            end_utc,
            [entity_id],
            None,
            include_start_time_state=True,
            significant_changes_only=False,
            minimal_response=False,
            no_attributes=False,
        )
    for state in states_map.get(entity_id) or []:
        rows = _detailed_rows_from_attrs(getattr(state, "attributes", None))
        if len(rows) < 2:
            continue
        fetched_ms = state.last_updated.timestamp() * 1000
        snapshots.append((fetched_ms, rows))
    return sorted(snapshots, key=lambda item: item[0])


def build_forecast_intraday_chart_for_range(
    *,
    snapshots: list[tuple[float, list[dict[str, Any]]]],
    day_start_ms: float,
    as_of_ms: float,
    include_future: bool,
) -> list[dict[str, float]]:
    """Build 5-minute forecast kW points for a local day up to as_of_ms."""
    if not snapshots:
        return []
    latest_rows = snapshots[-1][1]
    t_max_ms = day_start_ms + 24 * 60 * 60 * 1000
    out: list[dict[str, float]] = []
    slot = int(day_start_ms)
    while slot <= t_max_ms:
        if not include_future and slot > as_of_ms:
            break
        when = _utc_from_timestamp(slot / 1000)
        if include_future and slot > as_of_ms:
            rows = latest_rows
            kw_fn = _kw_at_or_after
        else:
            rows = _snapshot_for_time(snapshots, slot)
            kw_fn = _kw_at_time
        if rows:
            kw = kw_fn(rows, when)
            if kw is not None:
                out.append({"t": float(slot), "v": float(kw)})
        slot += STATISTICS_PERIOD_MS
    return out


def build_forecast_intraday_chart_for_day(
    hass: HomeAssistant,
    stored: dict[str, Any] | None,
    current_cache: dict[str, Any] | None,
    target_day: date,
    *,
    entry_id: str | None = None,
    use_daily_cache: bool = True,
    use_recorder: bool = True,
) -> list[dict[str, float]]:
    """Historical day chart: each slot uses the forecast known at that time."""
    day_key = target_day.isoformat()
    if use_daily_cache:
        cached = get_daily_intraday_points(stored, day_key)
        if cached:
            return cached

    day_start = dt_util.start_of_local_day(
        dt_util.as_local(datetime.combine(target_day, time.min))
    )
    day_start_ms = day_start.timestamp() * 1000
    day_end = day_start + timedelta(days=1)
    as_of_ms = day_end.timestamp() * 1000 - 1

    storage_snaps = collect_storage_snapshots(stored, current_cache, day_start_ms)
    recorder_snaps: list[tuple[float, list[dict[str, Any]]]] = []
    if use_recorder and entry_id:
        entity_id = find_solcast_forecast_entity(hass, entry_id)
        if entity_id:
            recorder_snaps = collect_recorder_snapshots(hass, entity_id, day_start, day_end)

    snapshots = _merge_snapshots(storage_snaps, recorder_snaps)
    return build_forecast_intraday_chart_for_range(
        snapshots=snapshots,
        day_start_ms=day_start_ms,
        as_of_ms=as_of_ms,
        include_future=False,
    )


def archive_daily_intraday_forecasts(
    hass: HomeAssistant,
    stored: dict[str, Any] | None,
    current_cache: dict[str, Any] | None,
    *,
    entry_id: str | None = None,
    days_back: int = 14,
    use_recorder: bool = True,
) -> dict[str, list[dict[str, float]]]:
    """Build and return per-day chart lines to persist for Analysis history navigation."""
    updates: dict[str, list[dict[str, float]]] = {}
    today = dt_util.as_local(dt_util.utcnow()).date()
    existing_daily = (stored or {}).get("daily_intraday") if isinstance(stored, dict) else {}
    if not isinstance(existing_daily, dict):
        existing_daily = {}
    for offset in range(0, max(0, days_back) + 1):
        target = today - timedelta(days=offset)
        key = target.isoformat()
        if offset > 0 and isinstance(existing_daily.get(key), list) and len(existing_daily[key]) >= 24:
            continue
        points = build_forecast_intraday_chart_for_day(
            hass,
            stored,
            current_cache,
            target,
            entry_id=entry_id,
            use_daily_cache=False,
            use_recorder=use_recorder,
        )
        if len(points) >= 2:
            updates[key] = points
    return updates


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
    snapshots = collect_storage_snapshots(stored, current_cache, day_start_ms)
    return build_forecast_intraday_chart_for_range(
        snapshots=snapshots,
        day_start_ms=day_start_ms,
        as_of_ms=now_ms,
        include_future=True,
    )


def build_statistics_forecast_overlay(
    hass: HomeAssistant,
    stored: dict[str, Any] | None,
    current_cache: dict[str, Any] | None,
) -> list[dict[str, float]]:
    """Statistics chart overlay: revision past + cached detailed forecast through end of day."""
    now = dt_util.now()
    day_start = dt_util.start_of_local_day(now)
    day_start_ms = day_start.timestamp() * 1000
    as_of_ms = now.timestamp() * 1000
    t_max_ms = day_start_ms + 24 * 60 * 60 * 1000

    snapshots = collect_storage_snapshots(stored, current_cache, day_start_ms)
    past: list[dict[str, float]] = []
    if snapshots:
        past = build_forecast_intraday_chart_for_range(
            snapshots=snapshots,
            day_start_ms=day_start_ms,
            as_of_ms=as_of_ms,
            include_future=False,
        )

    detailed_rows = _detailed_rows(current_cache) if current_cache else []
    if len(detailed_rows) < 2 and snapshots:
        detailed_rows = snapshots[-1][1]

    detailed_day: list[dict[str, float]] = []
    if len(detailed_rows) >= 2:
        slot = int(day_start_ms)
        while slot <= t_max_ms:
            when = _utc_from_timestamp(slot / 1000)
            kw = _kw_at_or_after(detailed_rows, when)
            if kw is not None:
                detailed_day.append({"t": float(slot), "v": float(kw)})
            slot += STATISTICS_PERIOD_MS

    if not detailed_day and len(detailed_rows) >= 2:
        detailed_day = build_forecast_intraday_chart_for_range(
            snapshots=[(as_of_ms, detailed_rows)],
            day_start_ms=day_start_ms,
            as_of_ms=as_of_ms,
            include_future=True,
        )

    if not past and not detailed_day:
        return []
    if not past:
        return detailed_day
    if not detailed_day:
        return past

    merged: dict[float, float] = {}
    for point in past:
        t = float(point["t"])
        if t <= as_of_ms:
            merged[t] = float(point["v"])
    grace_ms = float(STATISTICS_PERIOD_MS)
    for point in detailed_day:
        t = float(point["t"])
        if t >= as_of_ms - grace_ms:
            merged[t] = float(point["v"])
    return [{"t": t, "v": v} for t, v in sorted(merged.items()) if day_start_ms <= t <= t_max_ms]
