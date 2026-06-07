"""Compare Solcast PV forecast revisions against actual production."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .solcast_forecast_chart import (
    STATISTICS_PERIOD_MS,
    build_forecast_intraday_chart_for_day,
    build_forecast_intraday_chart_for_range,
    collect_storage_snapshots,
    find_solcast_forecast_entity,
    _merge_snapshots,
    _utc_from_timestamp,
)
from .solcast_forecast_metrics import _build_intervals, _local_date, _sum_kwh

_PV_POWER_KEYS = (
    "pv_power",
    "pv1_power",
    "pv_power_total",
    "pv_power_evo_10",
    "pv_power_now",
)
_ENERGY_TODAY_KEYS = ("solar_energy_today",)


def _resolve_entity(entity_map: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        entity_id = entity_map.get(key)
        if entity_id:
            return str(entity_id)
    return None


def _entity_value_to_kw(hass: HomeAssistant, entity_id: str, value: float) -> float:
    state = hass.states.get(entity_id)
    unit = ""
    if state:
        unit = str(state.attributes.get("unit_of_measurement") or "").lower()
    abs_v = abs(float(value))
    if unit in ("w", "watt", "watts") or abs_v > 50:
        return abs_v / 1000.0
    return abs_v


def _day_bounds(target_day: date) -> tuple[datetime, datetime, float, float]:
    day_start = dt_util.start_of_local_day(
        dt_util.as_local(datetime.combine(target_day, time.min))
    )
    day_end = day_start + timedelta(days=1)
    return (
        day_start,
        day_end,
        day_start.timestamp() * 1000,
        day_end.timestamp() * 1000,
    )


def _interpolate_kw(points: list[dict[str, float]], when_ms: float) -> float:
    if not points:
        return 0.0
    if when_ms <= points[0]["t"]:
        return max(0.0, points[0]["v"])
    if when_ms >= points[-1]["t"]:
        return max(0.0, points[-1]["v"])
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        if a["t"] <= when_ms <= b["t"]:
            span = b["t"] - a["t"]
            if span <= 0:
                return max(0.0, a["v"])
            ratio = (when_ms - a["t"]) / span
            return max(0.0, a["v"] + (b["v"] - a["v"]) * ratio)
    return max(0.0, points[-1]["v"])


def _integrate_kw_to_cumulative(
    power_kw: list[dict[str, float]],
    day_start_ms: float,
    as_of_ms: float,
) -> list[dict[str, float]]:
    if not power_kw:
        return []
    period_h = STATISTICS_PERIOD_MS / 3_600_000
    cum = 0.0
    out: list[dict[str, float]] = []
    slot = int(day_start_ms)
    end = int(as_of_ms)
    while slot <= end:
        kw = _interpolate_kw(power_kw, float(slot))
        cum += kw * period_h
        out.append({"t": float(slot), "v": round(cum, 3)})
        slot += STATISTICS_PERIOD_MS
    return out


def _forecast_kwh_for_day(rows: list[dict[str, Any]], target_day: date) -> float | None:
    intervals = _build_intervals(rows)
    if not intervals:
        return None
    total = _sum_kwh(intervals, day=target_day)
    return round(total, 3) if total > 0 else None


def _forecast_remaining_kwh(rows: list[dict[str, Any]], target_day: date, after: datetime) -> float | None:
    intervals = _build_intervals(rows)
    if not intervals:
        return None
    after_utc = dt_util.as_utc(after)
    total = _sum_kwh(intervals, day=target_day, after=after_utc)
    return round(total, 3) if total >= 0 else None


def _snapshots_for_target_day(
    hass: HomeAssistant,
    stored: dict[str, Any] | None,
    current_cache: dict[str, Any] | None,
    target_day: date,
    *,
    entry_id: str | None,
    use_recorder: bool = False,
) -> list[tuple[float, list[dict[str, Any]]]]:
    day_start, day_end, day_start_ms, _ = _day_bounds(target_day)
    storage_snaps = collect_storage_snapshots(stored, current_cache, day_start_ms)
    recorder_snaps: list[tuple[float, list[dict[str, Any]]]] = []
    if use_recorder and entry_id:
        from .solcast_forecast_chart import collect_recorder_snapshots

        entity_id = find_solcast_forecast_entity(hass, entry_id)
        if entity_id:
            recorder_snaps = collect_recorder_snapshots(hass, entity_id, day_start, day_end)
    merged = _merge_snapshots(storage_snaps, recorder_snaps)
    day_end_ms = day_end.timestamp() * 1000 - 1
    filtered: list[tuple[float, list[dict[str, Any]]]] = []
    for fetched_ms, rows in merged:
        if fetched_ms > day_end_ms:
            continue
        if len(rows) < 2:
            continue
        filtered.append((fetched_ms, rows))
    return filtered


def _actual_power_points(
    hass: HomeAssistant,
    entity_id: str,
    day_start: datetime,
    as_of: datetime,
) -> list[dict[str, float]]:
    from .websocket_api import _fetch_statistics_points

    start_utc = dt_util.as_utc(day_start)
    end_utc = dt_util.as_utc(as_of)
    stats = _fetch_statistics_points(
        hass,
        start_utc,
        end_utc,
        [entity_id],
        period="5minute",
        statistic="mean",
    )
    out: list[dict[str, float]] = []
    for row in stats.get(entity_id) or []:
        mean = row.get("mean")
        start = row.get("start")
        if mean is None or start is None:
            continue
        t_ms = float(start) * 1000 if start < 1e12 else float(start)
        out.append({"t": t_ms, "v": _entity_value_to_kw(hass, entity_id, float(mean))})
    out.sort(key=lambda p: p["t"])
    return out


def _actual_kwh_from_energy_sensor(
    hass: HomeAssistant,
    entity_id: str,
    day_start: datetime,
    as_of: datetime,
) -> float | None:
    from .websocket_api import _fetch_history_points

    start_utc = dt_util.as_utc(day_start - timedelta(minutes=5))
    end_utc = dt_util.as_utc(as_of)
    hist = _fetch_history_points(
        hass,
        start_utc,
        end_utc,
        [entity_id],
        significant_changes_only=False,
    )
    rows = hist.get(entity_id) or []
    values: list[tuple[float, float]] = [(row["t"], row["v"]) for row in rows if "t" in row and "v" in row]
    if not values:
        state = hass.states.get(entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                return round(float(state.state), 3)
            except (TypeError, ValueError):
                return None
        return None
    values.sort(key=lambda item: item[0])
    baseline = values[0][1]
    peak = baseline
    for _, val in values:
        if val >= baseline - 0.01:
            peak = max(peak, val)
    produced = max(0.0, peak - baseline)
    return round(produced, 3) if produced > 0 else None


def _hour_floor_local(when: datetime) -> datetime:
    local = dt_util.as_local(when)
    return local.replace(minute=0, second=0, microsecond=0)


def _hour_ceil_local(when: datetime) -> datetime:
    local = dt_util.as_local(when)
    floored = local.replace(minute=0, second=0, microsecond=0)
    if local == floored:
        return floored
    return floored + timedelta(hours=1)


def _chart_window_for_day(hass: HomeAssistant, target_day: date) -> dict[str, Any]:
    """Daylight chart bounds: hour containing sunrise through hour after sunset."""
    day_start, _, day_start_ms, _ = _day_bounds(target_day)
    fallback = {
        "t_min_ms": day_start_ms + 6 * 3_600_000,
        "t_max_ms": day_start_ms + 20 * 3_600_000,
        "sunrise": None,
        "sunset": None,
    }
    try:
        from homeassistant.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
        from homeassistant.helpers.sun import get_astral_event_date

        probe = dt_util.as_local(datetime.combine(target_day, time(12, 0)))
        sunrise = get_astral_event_date(hass, SUN_EVENT_SUNRISE, probe)
        sunset = get_astral_event_date(hass, SUN_EVENT_SUNSET, probe)
    except (TypeError, ValueError, KeyError):
        return fallback
    if sunrise is None or sunset is None:
        return fallback
    sunrise_local = dt_util.as_local(sunrise)
    sunset_local = dt_util.as_local(sunset)
    t_min = _hour_floor_local(sunrise_local)
    t_max = _hour_ceil_local(sunset_local)
    if t_max <= t_min:
        t_max = t_min + timedelta(hours=12)
    return {
        "t_min_ms": t_min.timestamp() * 1000,
        "t_max_ms": t_max.timestamp() * 1000,
        "sunrise": sunrise_local.isoformat(),
        "sunset": sunset_local.isoformat(),
    }


def _points_through(points: list[dict[str, float]], end_ms: float) -> list[dict[str, float]]:
    return [p for p in points if p["t"] <= end_ms]


def build_forecast_accuracy_report(
    hass: HomeAssistant,
    stored: dict[str, Any] | None,
    current_cache: dict[str, Any] | None,
    entity_map: dict[str, Any],
    target_day: date,
    *,
    entry_id: str | None = None,
    storm_prep: Any | None = None,
) -> dict[str, Any]:
    """Actual vs Solcast forecast with per-poll revision history for one local day."""
    day_start, day_end, day_start_ms, day_end_ms = _day_bounds(target_day)
    now = dt_util.now()
    local_today = dt_util.as_local(now).date()
    is_today = target_day == local_today
    as_of = min(now, day_end - timedelta(seconds=1))
    as_of_ms = as_of.timestamp() * 1000

    pv_entity = _resolve_entity(entity_map, _PV_POWER_KEYS)
    energy_entity = _resolve_entity(entity_map, _ENERGY_TODAY_KEYS)

    actual_power: list[dict[str, float]] = []
    if pv_entity:
        actual_power = _actual_power_points(hass, pv_entity, day_start, as_of)
    actual_cumulative = _integrate_kw_to_cumulative(actual_power, day_start_ms, as_of_ms)

    predicted_kw = build_forecast_intraday_chart_for_day(
        hass,
        stored,
        current_cache,
        target_day,
        entry_id=entry_id,
        use_daily_cache=True,
    )
    predicted_in_range = [p for p in predicted_kw if p["t"] <= as_of_ms]
    predicted_cumulative = _integrate_kw_to_cumulative(predicted_in_range, day_start_ms, as_of_ms)

    snapshots = _snapshots_for_target_day(
        hass, stored, current_cache, target_day, entry_id=entry_id
    )
    revisions: list[dict[str, Any]] = []
    prev_total: float | None = None
    for fetched_ms, rows in snapshots:
        when = _utc_from_timestamp(fetched_ms / 1000)
        when_local = dt_util.as_local(when)
        if _local_date(when_local) != target_day:
            continue
        total_kwh = _forecast_kwh_for_day(rows, target_day)
        remaining_kwh = _forecast_remaining_kwh(rows, target_day, when_local)
        if total_kwh is None and remaining_kwh is None:
            continue
        delta_kwh = None
        if total_kwh is not None and prev_total is not None:
            delta_kwh = round(total_kwh - prev_total, 3)
        if total_kwh is not None:
            prev_total = total_kwh
        revisions.append(
            {
                "fetched_at": when_local.isoformat(),
                "fetched_at_ms": fetched_ms,
                "forecast_today_kwh": total_kwh,
                "forecast_remaining_kwh": remaining_kwh,
                "delta_kwh": delta_kwh,
            }
        )

    first_curve: list[dict[str, float]] = []
    latest_curve: list[dict[str, float]] = []
    if snapshots:
        first_curve = build_forecast_intraday_chart_for_range(
            snapshots=[snapshots[0]],
            day_start_ms=day_start_ms,
            as_of_ms=as_of_ms,
            include_future=False,
        )
        latest_curve = build_forecast_intraday_chart_for_range(
            snapshots=[snapshots[-1]],
            day_start_ms=day_start_ms,
            as_of_ms=as_of_ms,
            include_future=False,
        )
    first_cumulative = _integrate_kw_to_cumulative(first_curve, day_start_ms, as_of_ms)
    latest_cumulative = _integrate_kw_to_cumulative(latest_curve, day_start_ms, as_of_ms)

    chart_window = _chart_window_for_day(hass, target_day)

    from .storm_weather import build_cloud_coverage_points, resolve_overview_weather_entities

    _, weather_entity_id = resolve_overview_weather_entities(hass, storm_prep)
    cloud_end_ms = chart_window["t_max_ms"] if is_today else as_of_ms
    cloud_coverage_pct = build_cloud_coverage_points(
        hass,
        weather_entity_id,
        day_start_ms=chart_window["t_min_ms"],
        as_of_ms=min(as_of_ms, chart_window["t_max_ms"]),
        t_max_ms=cloud_end_ms,
        period_ms=STATISTICS_PERIOD_MS,
    )

    actual_kwh = actual_cumulative[-1]["v"] if actual_cumulative else None
    if actual_kwh is None and energy_entity:
        actual_kwh = _actual_kwh_from_energy_sensor(hass, energy_entity, day_start, as_of)

    predicted_kwh = predicted_cumulative[-1]["v"] if predicted_cumulative else None
    first_predicted_kwh = revisions[0]["forecast_today_kwh"] if revisions else None
    latest_predicted_kwh = revisions[-1]["forecast_today_kwh"] if revisions else None

    error_kwh = None
    error_pct = None
    if actual_kwh is not None and predicted_kwh is not None:
        error_kwh = round(actual_kwh - predicted_kwh, 3)
        if predicted_kwh > 0.05:
            error_pct = round((error_kwh / predicted_kwh) * 100.0, 1)

    return {
        "day": target_day.isoformat(),
        "is_today": is_today,
        "as_of": dt_util.as_local(as_of).isoformat(),
        "actual_kwh": actual_kwh,
        "predicted_kwh": predicted_kwh,
        "first_predicted_kwh": first_predicted_kwh,
        "latest_predicted_kwh": latest_predicted_kwh,
        "error_kwh": error_kwh,
        "error_pct": error_pct,
        "revision_count": len(revisions),
        "revisions": revisions[-12:],
        "chart_window": chart_window,
        "intraday": {
            "actual_cumulative": actual_cumulative,
            "predicted_cumulative": predicted_cumulative,
            "first_revision_cumulative": first_cumulative,
            "latest_revision_cumulative": latest_cumulative,
            "actual_power_kw": actual_power,
            "predicted_power_kw": predicted_in_range,
            "latest_revision_power_kw": _points_through(latest_curve, as_of_ms),
            "cloud_coverage_pct": cloud_coverage_pct,
        },
        "weather_entity_id": weather_entity_id,
        "cloud_coverage_available": len(cloud_coverage_pct) >= 2,
        "solcast_enabled": bool(snapshots or predicted_kw),
    }
