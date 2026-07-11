"""Backfill SQLite intraday samples from HA recorder when gaps exist."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from ..performance_chart import (
    PERFORMANCE_SENSOR_KINDS,
    _stats_to_points,
    performance_entity_id,
)

_LOGGER = logging.getLogger(__name__)

MIN_SAMPLES_PER_DAY = 6
BACKFILL_DAYS = 7

_FIELD_FROM_KIND = {
    "pv_power_kw": "pv_power_kw",
    "net_grid_power_kw": "net_grid_power_kw",
    "virtual_panel_temp_c": "virtual_panel_temp_c",
    "wind_speed_ms": "wind_speed_ms",
    "clipping_loss_kw": "clipping_loss_kw",
    "solcast_forecast_kw": "solcast_forecast_kw",
    "visibility_km": "visibility_km",
    "dew_point_c": "dew_point_c",
    "precipitation_mm": "precipitation_mm",
}


def _day_bounds(target_day: date) -> tuple[datetime, datetime]:
    day_start = dt_util.start_of_local_day(
        dt_util.as_local(datetime.combine(target_day, time.min))
    )
    day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
    return day_start, day_end


def _bucket_key(t_ms: float) -> str:
    dt_local = dt_util.as_local(dt_util.utc_from_timestamp(t_ms / 1000.0))
    rounded = dt_local.replace(second=0, microsecond=0)
    minute = (rounded.minute // 5) * 5
    rounded = rounded.replace(minute=minute)
    return rounded.isoformat()


async def async_backfill_intraday_from_recorder(coordinator: Any) -> int:
    """Fill missing intraday buckets from recorder performance sensors."""
    store = getattr(coordinator, "_performance_store", None)
    if store is None or not coordinator.plant.performance.enabled:
        return 0

    hass = coordinator.hass
    entry_id = coordinator.config_entry.entry_id
    today = dt_util.as_local(dt_util.now()).date()
    inserted = 0

    from ..websocket_api import _fetch_statistics_points

    for offset in range(BACKFILL_DAYS):
        target_day = today - timedelta(days=offset)
        day_start, day_end = _day_bounds(target_day)
        existing = store.list_intraday_samples(day_start.isoformat(), day_end.isoformat())
        if len(existing) >= MIN_SAMPLES_PER_DAY:
            continue

        entity_ids: list[str] = []
        kind_for_entity: dict[str, str] = {}
        for kind in (*PERFORMANCE_SENSOR_KINDS, "visibility_km", "dew_point_c", "precipitation_mm"):
            eid = performance_entity_id(hass, entry_id, kind)
            if eid:
                entity_ids.append(eid)
                kind_for_entity[eid] = kind

        if not entity_ids:
            continue

        stats = _fetch_statistics_points(
            hass,
            dt_util.as_utc(day_start),
            dt_util.as_utc(day_end),
            entity_ids,
            period="5minute",
            statistic="mean",
        )

        buckets: dict[str, dict[str, Any]] = {}
        for eid, rows in stats.items():
            kind = kind_for_entity.get(eid)
            if not kind:
                continue
            field = _FIELD_FROM_KIND.get(kind, kind)
            for point in _stats_to_points(rows):
                key = _bucket_key(point["t"])
                bucket = buckets.setdefault(key, {"ts": key})
                bucket[field] = point["v"]

        for row in buckets.values():
            if row.get("ts") and any(k != "ts" for k in row):
                store.insert_intraday_sample(row)
                inserted += 1

    if inserted:
        _LOGGER.debug("Performance intraday backfill inserted %s buckets", inserted)
    return inserted
