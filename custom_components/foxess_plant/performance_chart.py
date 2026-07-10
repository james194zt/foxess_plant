"""Performance day chart — recorder statistics for panel UI."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .tariff_schedule import tariff_plugin_entity_id

_LOGGER = logging.getLogger(__name__)

PERFORMANCE_SENSOR_KINDS = (
    "pv_power_kw",
    "net_grid_power_kw",
    "virtual_panel_temp_c",
    "wind_speed_ms",
    "clipping_loss_kw",
    "solcast_forecast_kw",
)


def performance_entity_id(hass: HomeAssistant, entry_id: str, kind: str) -> str | None:
    reg = er.async_get(hass)
    if reg is None:
        return None
    return reg.async_get_entity_id("sensor", "foxess_plant", f"{entry_id}_performance_{kind}")


def resolve_performance_entities(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    entities: dict[str, str] = {}
    for kind in PERFORMANCE_SENSOR_KINDS:
        entity_id = performance_entity_id(hass, entry_id, kind)
        if entity_id:
            entities[kind] = entity_id
    import_id = tariff_plugin_entity_id(hass, entry_id, "import")
    if import_id:
        entities["import_rate"] = import_id
    export_id = tariff_plugin_entity_id(hass, entry_id, "export")
    if export_id:
        entities["export_rate"] = export_id
    return entities


def _stats_to_points(rows: list[dict[str, Any]], *, scale: float = 1.0) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for row in rows or []:
        raw_start = row.get("start")
        if raw_start is None:
            continue
        if isinstance(raw_start, datetime):
            t_ms = dt_util.as_timestamp(raw_start) * 1000
        else:
            try:
                t_ms = float(raw_start)
                if t_ms < 1e12:
                    t_ms *= 1000
            except (TypeError, ValueError):
                continue
        mean = row.get("mean")
        if mean is None:
            continue
        try:
            v = float(mean) * scale
        except (TypeError, ValueError):
            continue
        points.append({"t": t_ms, "v": round(v, 4)})
    return sorted(points, key=lambda p: p["t"])


def _day_bounds(target_day: date) -> tuple[datetime, datetime]:
    day_start = dt_util.start_of_local_day(
        dt_util.as_local(datetime.combine(target_day, time.min))
    )
    day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
    return day_start, day_end


async def async_build_performance_day_chart(
    hass: HomeAssistant,
    coordinator: Any,
    *,
    day: date | None = None,
) -> dict[str, Any]:
    """Build recorder-backed intraday series for the Performance report."""
    from .performance.tick import performance_summary
    from .websocket_api import _fetch_statistics_points

    entry_id = coordinator.config_entry.entry_id
    target_day = day or dt_util.as_local(dt_util.now()).date()
    day_start, day_end = _day_bounds(target_day)
    start_utc = dt_util.as_utc(day_start)
    end_utc = dt_util.as_utc(day_end)

    entities = resolve_performance_entities(hass, entry_id)
    entity_ids = list(entities.values())
    stats: dict[str, list[dict[str, Any]]] = {}
    if entity_ids:
        stats = _fetch_statistics_points(
            hass,
            start_utc,
            end_utc,
            entity_ids,
            period="5minute",
            statistic="mean",
        )

    kind_to_entity = {kind: eid for kind, eid in entities.items()}
    series: dict[str, list[dict[str, float]]] = {}
    for kind in PERFORMANCE_SENSOR_KINDS:
        eid = kind_to_entity.get(kind)
        if eid:
            series[kind] = _stats_to_points(stats.get(eid, []))

    import_eid = kind_to_entity.get("import_rate")
    if import_eid:
        series["import_rate_p_kwh"] = _stats_to_points(stats.get(import_eid, []), scale=100.0)
    export_eid = kind_to_entity.get("export_rate")
    if export_eid:
        series["export_rate_p_kwh"] = _stats_to_points(stats.get(export_eid, []), scale=100.0)

    cfg = coordinator.plant.performance
    summary = performance_summary(coordinator)
    analytics = coordinator._read_analytics()
    pv_kwh = analytics.get("pv_production_kwh_today")
    solcast_state = coordinator._solcast_state()
    forecast_kwh = solcast_state.get("forecast_today_kwh")
    accuracy_pct = None
    if pv_kwh and forecast_kwh:
        try:
            accuracy_pct = round(float(pv_kwh) / float(forecast_kwh) * 100.0, 1)
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    return {
        "day": target_day.isoformat(),
        "enabled": cfg.enabled,
        "entities": entities,
        "series": series,
        "ac_limit_kw": cfg.inverter_ac_limit_kw,
        "summary": summary,
        "live": {
            "pv_kwh_today": pv_kwh,
            "solcast_forecast_kwh": forecast_kwh,
            "forecast_accuracy_pct": accuracy_pct,
            "import_p_per_kwh": coordinator._octopus_cache.get("current_import_p_per_kwh"),
            "export_p_per_kwh": coordinator._octopus_cache.get("current_export_p_per_kwh"),
        },
        "chart_window": {
            "start_ms": day_start.timestamp() * 1000,
            "end_ms": day_end.timestamp() * 1000,
            "now_ms": min(dt_util.now().timestamp() * 1000, day_end.timestamp() * 1000),
        },
    }
