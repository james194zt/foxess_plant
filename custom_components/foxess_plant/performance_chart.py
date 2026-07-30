"""Performance day chart — SQLite intraday samples with recorder fallbacks."""

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
    "visibility_km",
    "dew_point_c",
    "precipitation_mm",
    "clipping_loss_kw",
    "solcast_forecast_kw",
)

MODBUS_FALLBACK_KEYS: dict[str, str] = {
    "pv_power_kw": "pv_power",
}

SAMPLE_FIELD_TO_SERIES = {
    "pv_power_kw": "pv_power_kw",
    "net_grid_power_kw": "net_grid_power_kw",
    "virtual_panel_temp_c": "virtual_panel_temp_c",
    "wind_speed_ms": "wind_speed_ms",
    "visibility_km": "visibility_km",
    "dew_point_c": "dew_point_c",
    "precipitation_mm": "precipitation_mm",
    "clipping_loss_kw": "clipping_loss_kw",
    "solcast_forecast_kw": "solcast_forecast_kw",
    "import_p_per_kwh": "import_rate_p_kwh",
    "export_p_per_kwh": "export_rate_p_kwh",
}


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


def _sample_ts_to_ms(raw_ts: str) -> float | None:
    parsed = dt_util.parse_datetime(str(raw_ts))
    if parsed is None:
        return None
    return dt_util.as_local(parsed).timestamp() * 1000


def _samples_to_series(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, float]]]:
    series: dict[str, list[dict[str, float]]] = {kind: [] for kind in PERFORMANCE_SENSOR_KINDS}
    series["import_rate_p_kwh"] = []
    series["export_rate_p_kwh"] = []
    for row in rows:
        t_ms = _sample_ts_to_ms(row.get("ts", ""))
        if t_ms is None:
            continue
        for field, series_key in SAMPLE_FIELD_TO_SERIES.items():
            raw = row.get(field)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if series_key.endswith("_p_kwh"):
                value *= 100.0
            series[series_key].append({"t": t_ms, "v": round(value, 4)})
    for key in series:
        series[key].sort(key=lambda p: p["t"])
    return series


def _merge_series(
    primary: dict[str, list[dict[str, float]]],
    secondary: dict[str, list[dict[str, float]]],
) -> dict[str, list[dict[str, float]]]:
    merged = {key: list(primary.get(key) or []) for key in set(primary) | set(secondary)}
    for key, pts in secondary.items():
        if len(merged.get(key) or []) >= len(pts or []):
            continue
        merged[key] = list(pts or [])
    return merged


def _resolve_modbus_entity(hass: HomeAssistant, coordinator: Any, key: str) -> str | None:
    from .discovery import resolve_entity_id

    return resolve_entity_id(
        hass,
        coordinator.plant.entity_map,
        key,
        device_id=coordinator.plant.device_id,
    )


def _modbus_fallback_series(
    hass: HomeAssistant,
    coordinator: Any,
    *,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, list[dict[str, float]]]:
    from .websocket_api import _fetch_statistics_points

    series: dict[str, list[dict[str, float]]] = {kind: [] for kind in PERFORMANCE_SENSOR_KINDS}
    for kind, map_key in MODBUS_FALLBACK_KEYS.items():
        entity_id = _resolve_modbus_entity(hass, coordinator, map_key)
        if not entity_id:
            continue
        stats = _fetch_statistics_points(
            hass,
            start_utc,
            end_utc,
            [entity_id],
            period="5minute",
            statistic="mean",
        )
        pts = _stats_to_points(stats.get(entity_id, []))
        if pts and max(p["v"] for p in pts) > 50:
            for point in pts:
                point["v"] = round(point["v"] / 1000.0, 4)
        if pts:
            series[kind] = pts
    return series


def _recorder_series(
    hass: HomeAssistant,
    entry_id: str,
    *,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, list[dict[str, float]]]:
    from .websocket_api import _fetch_statistics_points

    entities = resolve_performance_entities(hass, entry_id)
    entity_ids = [entities[k] for k in PERFORMANCE_SENSOR_KINDS if k in entities]
    if not entity_ids:
        return {kind: [] for kind in PERFORMANCE_SENSOR_KINDS}

    stats = _fetch_statistics_points(
        hass,
        start_utc,
        end_utc,
        entity_ids,
        period="5minute",
        statistic="mean",
    )
    kind_to_entity = {kind: entities[kind] for kind in PERFORMANCE_SENSOR_KINDS if kind in entities}
    series: dict[str, list[dict[str, float]]] = {}
    for kind in PERFORMANCE_SENSOR_KINDS:
        eid = kind_to_entity.get(kind)
        series[kind] = _stats_to_points(stats.get(eid, [])) if eid else []
    return series


def _entity_unit(hass: HomeAssistant, entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if not state:
        return None
    unit = state.attributes.get("unit_of_measurement")
    return str(unit) if unit else None


def _convert_weather_points(
    points: list[dict[str, float]],
    *,
    kind: str,
    unit: str | None,
) -> list[dict[str, float]]:
    from .performance.weather import (
        _rate_to_bucket_mm,
        _to_dew_point_c,
        _to_visibility_km,
        _to_wind_speed_ms,
    )

    out: list[dict[str, float]] = []
    for point in points:
        try:
            raw = float(point["v"])
        except (TypeError, ValueError, KeyError):
            continue
        if kind == "wind_speed_ms":
            value = _to_wind_speed_ms(raw, unit)
        elif kind == "visibility_km":
            value = _to_visibility_km(raw, unit)
        elif kind == "dew_point_c":
            value = _to_dew_point_c(raw, unit)
        elif kind == "precipitation_mm":
            value = _rate_to_bucket_mm(raw, unit)
        else:
            value = raw
        out.append({"t": point["t"], "v": round(float(value), 4)})
    return out


def _downsample_points(
    points: list[dict[str, float]],
    *,
    bucket_ms: int = 5 * 60 * 1000,
) -> list[dict[str, float]]:
    """Keep ~one point per bucket so raw history does not overwhelm the chart."""
    if not points:
        return []
    ordered = sorted(points, key=lambda p: p["t"])
    out: list[dict[str, float]] = []
    bucket_start = None
    bucket_point: dict[str, float] | None = None
    for point in ordered:
        t_ms = float(point["t"])
        start = t_ms - (t_ms % bucket_ms)
        if bucket_start is None or start != bucket_start:
            if bucket_point is not None:
                out.append(bucket_point)
            bucket_start = start
            bucket_point = {"t": t_ms, "v": float(point["v"])}
        else:
            bucket_point = {"t": t_ms, "v": float(point["v"])}
    if bucket_point is not None:
        out.append(bucket_point)
    return out


def _mapped_local_weather_series(
    hass: HomeAssistant,
    coordinator: Any,
    *,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, list[dict[str, float]]]:
    """Pull chart history directly from mapped PWS sensors (not only foxess_plant sensors)."""
    from .websocket_api import _fetch_history_points, _fetch_statistics_points

    cfg = coordinator.plant.performance
    role_to_kind = (
        ("wind_speed_entity_id", "wind_speed_ms"),
        ("visibility_entity_id", "visibility_km"),
        ("dew_point_entity_id", "dew_point_c"),
        ("precipitation_entity_id", "precipitation_mm"),
    )
    series: dict[str, list[dict[str, float]]] = {kind: [] for kind in PERFORMANCE_SENSOR_KINDS}
    entity_by_kind: dict[str, str] = {}
    for role, kind in role_to_kind:
        entity_id = getattr(cfg, role, None)
        if entity_id:
            entity_by_kind[kind] = str(entity_id)
    if not entity_by_kind:
        return series

    entity_ids = list(entity_by_kind.values())
    stats = _fetch_statistics_points(
        hass,
        start_utc,
        end_utc,
        entity_ids,
        period="5minute",
        statistic="mean",
    )
    # Ecowitt / PWS entities often have state history but no short-term statistics yet.
    need_history = [
        eid for eid in entity_ids if len(_stats_to_points(stats.get(eid, []))) < 2
    ]
    history_map: dict[str, list[dict[str, float]]] = {}
    if need_history:
        try:
            history_map = _fetch_history_points(
                hass,
                start_utc,
                end_utc,
                need_history,
                significant_changes_only=False,
            )
        except Exception as err:
            _LOGGER.debug("Local weather history fallback failed: %s", err)

    for kind, entity_id in entity_by_kind.items():
        pts = _stats_to_points(stats.get(entity_id, []))
        if len(pts) < 2:
            pts = _downsample_points(history_map.get(entity_id) or [])
        unit = _entity_unit(hass, entity_id)
        series[kind] = _convert_weather_points(pts, kind=kind, unit=unit)
    return series


def _points_to_lookup(points: list[dict[str, float]], *, bucket_ms: int = 5 * 60 * 1000) -> dict[int, float]:
    lookup: dict[int, float] = {}
    for point in _downsample_points(points, bucket_ms=bucket_ms):
        bucket = int(point["t"] - (point["t"] % bucket_ms))
        lookup[bucket] = float(point["v"])
    return lookup


def _virtual_panel_temp_from_inverter_history(
    hass: HomeAssistant,
    coordinator: Any,
    *,
    start_utc: datetime,
    end_utc: datetime,
) -> list[dict[str, float]]:
    """Rebuild virtual panel °C from PV voltage + power history when samples are empty."""
    from .discovery import resolve_entity_id
    from .performance.virtual_panel_temp import (
        compute_virtual_panel_temp_c,
        suggest_baseline_v_at_25c,
        voltage_out_of_baseline_band,
    )
    from .websocket_api import _fetch_history_points, _fetch_statistics_points

    cfg = coordinator.plant.performance
    device_id = coordinator.plant.device_id
    entity_map = coordinator.plant.entity_map
    baseline = float(cfg.baseline_v_at_25c)
    coeff = float(cfg.temp_coefficient_v_per_c)
    ac_limit = cfg.inverter_ac_limit_kw

    volt_ids: list[str] = []
    for key in (
        "pv1_voltage",
        "pv2_voltage",
        "pv3_voltage",
        "pv4_voltage",
        "pv1_volts",
        "pv2_volts",
    ):
        eid = resolve_entity_id(hass, entity_map, key, device_id=device_id)
        if eid and eid not in volt_ids:
            volt_ids.append(eid)

    power_id = resolve_entity_id(hass, entity_map, "pv_power", device_id=device_id)
    if not power_id:
        for key in ("pv1_power", "pv_power_total"):
            power_id = resolve_entity_id(hass, entity_map, key, device_id=device_id)
            if power_id:
                break
    if not volt_ids or not power_id:
        return []

    entity_ids = [*volt_ids, power_id]
    stats = _fetch_statistics_points(
        hass, start_utc, end_utc, entity_ids, period="5minute", statistic="mean"
    )
    history_needed = [
        eid for eid in entity_ids if len(_stats_to_points(stats.get(eid, []))) < 2
    ]
    history_map: dict[str, list[dict[str, float]]] = {}
    if history_needed:
        try:
            history_map = _fetch_history_points(
                hass, start_utc, end_utc, history_needed, significant_changes_only=False
            )
        except Exception as err:
            _LOGGER.debug("Virtual panel temp history fallback failed: %s", err)

    def series_for(entity_id: str) -> list[dict[str, float]]:
        pts = _stats_to_points(stats.get(entity_id, []))
        if len(pts) < 2:
            pts = _downsample_points(history_map.get(entity_id) or [])
        return pts

    power_lookup = _points_to_lookup(series_for(power_id))
    volt_lookups = [_points_to_lookup(series_for(eid)) for eid in volt_ids]
    buckets = sorted(set(power_lookup) | {b for lu in volt_lookups for b in lu})
    out: list[dict[str, float]] = []
    working_baseline = baseline
    for bucket in buckets:
        voltages = [lu[bucket] for lu in volt_lookups if bucket in lu and lu[bucket] > 50]
        if not voltages or bucket not in power_lookup:
            continue
        pv_kw = float(power_lookup[bucket])
        # Stats/history may be in W for some entities.
        if pv_kw > 50:
            pv_kw /= 1000.0
        string_v = sum(voltages) / len(voltages)
        temp = compute_virtual_panel_temp_c(
            string_voltage_v=string_v,
            pv_power_kw=pv_kw,
            baseline_v_at_25c=working_baseline,
            temp_coefficient_v_per_c=coeff,
            inverter_ac_limit_kw=ac_limit,
            ambient_temp_c=None,
        )
        if temp is None and voltage_out_of_baseline_band(
            live_v=string_v, baseline_v=working_baseline
        ):
            seeded = suggest_baseline_v_at_25c(
                string_voltage_v=string_v,
                ambient_temp_c=None,
                pv_power_kw=pv_kw,
                inverter_ac_limit_kw=ac_limit,
                temp_coefficient_v_per_c=coeff,
            )
            if seeded is not None:
                working_baseline = seeded
                temp = compute_virtual_panel_temp_c(
                    string_voltage_v=string_v,
                    pv_power_kw=pv_kw,
                    baseline_v_at_25c=working_baseline,
                    temp_coefficient_v_per_c=coeff,
                    inverter_ac_limit_kw=ac_limit,
                    ambient_temp_c=None,
                )
        if temp is None:
            continue
        out.append({"t": float(bucket), "v": float(temp)})
    return out


def _append_live_weather_point(
    series: dict[str, list[dict[str, float]]],
    coordinator: Any,
    *,
    is_today: bool,
) -> None:
    if not is_today:
        return
    sample = getattr(coordinator, "_last_performance_sample", None)
    if sample is None:
        return
    now_ms = dt_util.now().timestamp() * 1000
    live_map = {
        "virtual_panel_temp_c": sample.virtual_panel_temp_c,
        "wind_speed_ms": sample.wind_speed_ms,
        "visibility_km": sample.visibility_km,
        "dew_point_c": sample.dew_point_c,
        "precipitation_mm": sample.precipitation_mm,
    }
    for key, value in live_map.items():
        if value is None:
            continue
        try:
            point = {"t": now_ms, "v": round(float(value), 4)}
        except (TypeError, ValueError):
            continue
        pts = series.setdefault(key, [])
        if pts and abs(pts[-1]["t"] - now_ms) < 60_000:
            pts[-1] = point
        else:
            pts.append(point)
        pts.sort(key=lambda p: p["t"])


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
    """Build intraday series for the Performance report."""
    from .performance.tick import performance_summary

    entry_id = coordinator.config_entry.entry_id
    target_day = day or dt_util.as_local(dt_util.now()).date()
    day_start, day_end = _day_bounds(target_day)
    start_utc = dt_util.as_utc(day_start)
    end_utc = dt_util.as_utc(day_end)

    store = getattr(coordinator, "_performance_store", None)
    sqlite_rows: list[dict[str, Any]] = []
    if store is not None:
        sqlite_rows = store.list_intraday_samples(day_start.isoformat(), day_end.isoformat())

    series = _samples_to_series(sqlite_rows)
    sample_count = len(sqlite_rows)

    recorder_series = _recorder_series(hass, entry_id, start_utc=start_utc, end_utc=end_utc)
    series = _merge_series(series, recorder_series)
    local_weather_series = _mapped_local_weather_series(
        hass, coordinator, start_utc=start_utc, end_utc=end_utc
    )
    series = _merge_series(series, local_weather_series)
    if len(series.get("virtual_panel_temp_c") or []) < 12:
        temp_from_inverter = _virtual_panel_temp_from_inverter_history(
            hass, coordinator, start_utc=start_utc, end_utc=end_utc
        )
        if temp_from_inverter:
            series = _merge_series(
                series, {"virtual_panel_temp_c": temp_from_inverter}
            )
    _append_live_weather_point(series, coordinator, is_today=target_day == dt_util.as_local(dt_util.now()).date())

    if sample_count < 6:
        modbus_series = _modbus_fallback_series(
            hass, coordinator, start_utc=start_utc, end_utc=end_utc
        )
        series = _merge_series(series, modbus_series)

    entities = resolve_performance_entities(hass, entry_id)
    kind_to_entity = {kind: eid for kind, eid in entities.items()}
    stats: dict[str, list[dict[str, Any]]] = {}
    rate_entity_ids = [
        eid for key in ("import_rate", "export_rate") if (eid := kind_to_entity.get(key))
    ]
    if rate_entity_ids:
        from .websocket_api import _fetch_statistics_points

        stats = _fetch_statistics_points(
            hass,
            start_utc,
            end_utc,
            rate_entity_ids,
            period="5minute",
            statistic="mean",
        )

    if not series.get("import_rate_p_kwh"):
        import_eid = kind_to_entity.get("import_rate")
        if import_eid:
            series["import_rate_p_kwh"] = _stats_to_points(stats.get(import_eid, []), scale=100.0)
    if not series.get("export_rate_p_kwh"):
        export_eid = kind_to_entity.get("export_rate")
        if export_eid:
            series["export_rate_p_kwh"] = _stats_to_points(stats.get(export_eid, []), scale=100.0)

    from .performance.solar_analysis import payback_summary, solar_day_class_label

    cfg = coordinator.plant.performance
    day_iso = target_day.isoformat()
    is_today = target_day == dt_util.as_local(dt_util.now()).date()
    ledger_row = store.get_daily_ledger(day_iso) if store else None

    if ledger_row:
        payback = payback_summary(
            total_saved_gbp=store.sum_net_savings() if store else 0.0,
            install_cost_gbp=cfg.system_install_cost_gbp,
            avg_daily_savings_gbp=store.avg_net_savings_days(90) if store else None,
        )
        today_row = {
            **ledger_row,
            "solar_day_class_label": solar_day_class_label(ledger_row.get("solar_day_class")),
        }
        summary = {"enabled": cfg.enabled, "config": cfg.to_dict(), "today": today_row, **payback}
    elif is_today:
        summary = performance_summary(coordinator)
    else:
        summary = {"enabled": cfg.enabled, "today": {"date": day_iso}}

    analytics = coordinator._read_analytics()
    pv_kwh = ledger_row.get("pv_kwh") if ledger_row else analytics.get("pv_production_kwh_today")
    solcast_state = coordinator._solcast_state()
    forecast_kwh = (
        ledger_row.get("solcast_forecast_kwh")
        if ledger_row
        else solcast_state.get("forecast_today_kwh")
    )
    accuracy_pct = ledger_row.get("forecast_accuracy_pct") if ledger_row else None
    if accuracy_pct is None and pv_kwh and forecast_kwh:
        try:
            accuracy_pct = round(float(pv_kwh) / float(forecast_kwh) * 100.0, 1)
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    today_summary = summary.get("today") or {}
    physics_insights: list[str] = []
    if series:
        from .performance.physics_insights import build_intraday_physics_insights

        physics_insights = build_intraday_physics_insights(series, ac_limit_kw=cfg.inverter_ac_limit_kw)

    clipping_kwh_today = None
    if ledger_row and ledger_row.get("clipping_loss_kwh") is not None:
        clipping_kwh_today = ledger_row.get("clipping_loss_kwh")
    elif is_today:
        acc = getattr(coordinator, "_performance_daily", None) or {}
        clipping_kwh_today = acc.get("clipping_loss_kwh")

    chart_source = "sqlite" if sample_count >= 6 else "mixed"
    if sample_count == 0 and any(series.get(k) for k in PERFORMANCE_SENSOR_KINDS):
        chart_source = "recorder_fallback"

    sample = getattr(coordinator, "_last_performance_sample", None)
    live_metrics: dict[str, Any] = {}
    if sample is not None:
        live_metrics = {
            "virtual_panel_temp_c": sample.virtual_panel_temp_c,
            "wind_speed_ms": sample.wind_speed_ms,
            "visibility_km": sample.visibility_km,
            "dew_point_c": sample.dew_point_c,
        }

    return {
        "day": day_iso,
        "enabled": cfg.enabled,
        "config": cfg.to_dict(),
        "entities": entities,
        "series": series,
        "ac_limit_kw": cfg.inverter_ac_limit_kw,
        "summary": summary,
        "ledger": ledger_row,
        "live": {
            "pv_kwh_today": pv_kwh,
            "solcast_forecast_kwh": forecast_kwh,
            "forecast_accuracy_pct": accuracy_pct,
            "import_p_per_kwh": coordinator._octopus_cache.get("current_import_p_per_kwh"),
            "export_p_per_kwh": coordinator._octopus_cache.get("current_export_p_per_kwh"),
            "solar_day_class_label": today_summary.get("solar_day_class_label"),
            "insight_note": today_summary.get("insight_note"),
            "temp_adjusted_index_pct": today_summary.get("temp_adjusted_index_pct"),
            "clipping_kwh_today": clipping_kwh_today,
            "sample_count": sample_count,
            "chart_source": chart_source,
            **live_metrics,
        },
        "physics_insights": physics_insights,
        "chart_window": {
            "start_ms": day_start.timestamp() * 1000,
            "end_ms": day_end.timestamp() * 1000,
            "now_ms": min(dt_util.now().timestamp() * 1000, day_end.timestamp() * 1000),
        },
    }
