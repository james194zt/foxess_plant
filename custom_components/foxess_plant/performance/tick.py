"""Five-minute performance tick — sample, accumulate, midnight ledger commit."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .financial import (
    accumulate_bucket_financials,
    bucket_financials_gbp,
    estimate_bucket_energy_kwh,
    net_daily_savings_gbp,
)
from .sample import collect_performance_sample
from .store import PerformanceStore

_LOGGER = logging.getLogger(__name__)


def performance_db_path(hass: Any, entry_id: str) -> str:
    return str(hass.config.path("foxess_plant") / f"performance_{entry_id}.db")


def new_daily_accumulator() -> dict[str, Any]:
    return {
        "export_earnings_gbp": 0.0,
        "import_spend_gbp": 0.0,
        "avoided_grid_cost_gbp": 0.0,
        "net_bucket_gbp": 0.0,
        "import_kwh": 0.0,
        "export_kwh": 0.0,
        "clipping_loss_kwh": 0.0,
        "clipping_loss_valuation_gbp": 0.0,
        "peak_power_kw": 0.0,
        "pv_kwh_today": None,
        "solcast_forecast_kwh_today": None,
    }


def _forecast_accuracy_pct(actual: float | None, forecast: float | None) -> float | None:
    if actual is None or forecast is None or forecast <= 0:
        return None
    return round(actual / forecast * 100.0, 1)


async def async_performance_tick(coordinator: Any) -> None:
    """Run one 5-minute performance sample cycle."""
    if not coordinator.plant.performance.enabled:
        return

    local_now = dt_util.as_local(dt_util.now())
    local_date = local_now.date().isoformat()

    if coordinator._performance_day != local_date:
        if coordinator._performance_day:
            await async_commit_daily_ledger(coordinator, coordinator._performance_day)
        store: PerformanceStore | None = coordinator._performance_store
        if store is not None:
            try:
                purge_before = (local_now - timedelta(days=8)).isoformat()
                store.purge_intraday_before(purge_before)
            except Exception as err:
                _LOGGER.debug("Intraday sample purge skipped: %s", err)
        coordinator._performance_day = local_date
        coordinator._performance_daily = new_daily_accumulator()
        coordinator._performance_recent_peak_kw = 0.0

    sample = collect_performance_sample(coordinator)
    await coordinator.async_update_performance_sensors(sample)

    store = coordinator._performance_store
    if store is not None:
        bucket_ts = local_now.replace(second=0, microsecond=0)
        store.insert_intraday_sample(
            {
                "ts": bucket_ts.isoformat(),
                "pv_power_kw": sample.pv_power_kw,
                "net_grid_power_kw": sample.net_grid_power_kw,
                "virtual_panel_temp_c": sample.virtual_panel_temp_c,
                "wind_speed_ms": sample.wind_speed_ms,
                "clipping_loss_kw": sample.clipping_loss_kw,
                "solcast_forecast_kw": sample.solcast_forecast_kw,
                "import_p_per_kwh": sample.import_p_per_kwh,
                "export_p_per_kwh": sample.export_p_per_kwh,
            }
        )

    acc = coordinator._performance_daily
    if sample.pv_kwh_today is not None:
        acc["pv_kwh_today"] = sample.pv_kwh_today
    if sample.solcast_forecast_kwh_today is not None:
        acc["solcast_forecast_kwh_today"] = sample.solcast_forecast_kwh_today

    import_kwh = estimate_bucket_energy_kwh(
        abs(sample.net_grid_power_kw) if (sample.net_grid_power_kw or 0) < 0 else None
    )
    export_kwh = estimate_bucket_energy_kwh(
        sample.net_grid_power_kw if (sample.net_grid_power_kw or 0) > 0 else None
    )
    load_kwh = estimate_bucket_energy_kwh(sample.load_power_kw)

    imp_p = sample.import_p_per_kwh or 0.0
    exp_p = sample.export_p_per_kwh or 0.0
    financials = bucket_financials_gbp(
        import_kwh=import_kwh,
        export_kwh=export_kwh,
        load_kwh=load_kwh,
        import_p_per_kwh=imp_p,
        export_p_per_kwh=exp_p,
    )

    clip_kwh = estimate_bucket_energy_kwh(sample.clipping_loss_kw)
    clip_val = clip_kwh * exp_p / 100.0 if exp_p else 0.0

    bucket = {
        **financials,
        "import_kwh": import_kwh,
        "export_kwh": export_kwh,
        "clipping_loss_kwh": clip_kwh,
        "clipping_loss_valuation_gbp": round(clip_val, 4),
        "pv_power_kw": sample.pv_power_kw or 0.0,
        "virtual_panel_temp_c": sample.virtual_panel_temp_c,
    }
    accumulate_bucket_financials(coordinator._performance_daily, bucket)


async def async_commit_daily_ledger(coordinator: Any, date: str) -> None:
    """Flush accumulated daily metrics to SQLite."""
    from .solar_analysis import build_daily_insight, classify_forecast_day

    store: PerformanceStore | None = coordinator._performance_store
    if store is None:
        return

    acc = coordinator._performance_daily or new_daily_accumulator()
    cfg = coordinator.plant.performance

    pv_kwh = acc.get("pv_kwh_today")
    solcast_kwh = acc.get("solcast_forecast_kwh_today")
    forecast_accuracy = _forecast_accuracy_pct(
        float(pv_kwh) if pv_kwh is not None else None,
        float(solcast_kwh) if solcast_kwh is not None else None,
    )
    peak = float(acc.get("peak_power_kw") or 0.0)
    peak_vs_rated = None
    if cfg.inverter_ac_limit_kw > 0 and peak > 0:
        peak_vs_rated = round(peak / cfg.inverter_ac_limit_kw * 100.0, 1)

    solar_day_class = classify_forecast_day(
        forecast_accuracy_pct=forecast_accuracy,
        peak_vs_rated_pct=peak_vs_rated,
    )
    clipping_kwh = float(acc.get("clipping_loss_kwh") or 0.0)
    insight_note = build_daily_insight(
        forecast_accuracy_pct=forecast_accuracy,
        peak_vs_rated_pct=peak_vs_rated,
        solar_day_class=solar_day_class,
        virtual_temp_min_c=acc.get("virtual_temp_min_c"),
        virtual_temp_max_c=acc.get("virtual_temp_max_c"),
        clipping_loss_kwh=clipping_kwh,
    )

    row = {
        "date": date,
        "pv_kwh": pv_kwh,
        "solcast_forecast_kwh": solcast_kwh,
        "forecast_accuracy_pct": forecast_accuracy,
        "export_kwh": round(float(acc.get("export_kwh") or 0.0), 3),
        "import_kwh": round(float(acc.get("import_kwh") or 0.0), 3),
        "export_earnings_gbp": round(float(acc.get("export_earnings_gbp") or 0.0), 2),
        "import_spend_gbp": round(float(acc.get("import_spend_gbp") or 0.0), 2),
        "avoided_grid_cost_gbp": round(float(acc.get("avoided_grid_cost_gbp") or 0.0), 2),
        "clipping_loss_kwh": round(clipping_kwh, 3),
        "clipping_loss_valuation_gbp": round(float(acc.get("clipping_loss_valuation_gbp") or 0.0), 2),
        "net_daily_savings_gbp": net_daily_savings_gbp(acc),
        "peak_power_kw": round(peak, 2) if peak else None,
        "peak_vs_rated_pct": peak_vs_rated,
        "virtual_temp_min_c": acc.get("virtual_temp_min_c"),
        "virtual_temp_max_c": acc.get("virtual_temp_max_c"),
        "wind_correlation_note": insight_note,
        "solar_day_class": solar_day_class,
        "insight_note": insight_note,
    }
    store.upsert_daily_ledger(row)
    _LOGGER.debug("Performance daily ledger committed for %s", date)


async def async_init_performance_store(coordinator: Any) -> None:
    """Open SQLite store and sync payback config."""
    path = performance_db_path(coordinator.hass, coordinator.config_entry.entry_id)
    store = PerformanceStore(path)
    store.init_schema()
    coordinator._performance_store = store
    cfg = coordinator.plant.performance
    store.set_payback_config(
        install_cost_gbp=cfg.system_install_cost_gbp,
        install_date=coordinator.plant.solcast.installation_date,
        system_rte=cfg.system_rte,
    )


def performance_summary(coordinator: Any) -> dict[str, Any]:
    """Panel-friendly performance snapshot."""
    from .solar_analysis import payback_summary, solar_day_class_label

    store: PerformanceStore | None = getattr(coordinator, "_performance_store", None)
    cfg = coordinator.plant.performance
    today = coordinator._performance_day or dt_util.as_local(dt_util.now()).date().isoformat()
    acc = coordinator._performance_daily or {}
    ledger_today = store.get_daily_ledger(today) if store else None
    total_saved = store.sum_net_savings() if store else 0.0
    avg_90 = store.avg_net_savings_days(90) if store else None
    payback = payback_summary(
        total_saved_gbp=total_saved,
        install_cost_gbp=cfg.system_install_cost_gbp,
        avg_daily_savings_gbp=avg_90,
    )
    today_row = ledger_today or {
        "date": today,
        "net_daily_savings_gbp": net_daily_savings_gbp(acc) if acc else 0.0,
        "export_earnings_gbp": acc.get("export_earnings_gbp"),
        "import_spend_gbp": acc.get("import_spend_gbp"),
        "avoided_grid_cost_gbp": acc.get("avoided_grid_cost_gbp"),
    }
    if today_row.get("solar_day_class"):
        today_row = {
            **today_row,
            "solar_day_class_label": solar_day_class_label(today_row.get("solar_day_class")),
        }
    return {
        "enabled": cfg.enabled,
        "config": cfg.to_dict(),
        "today": today_row,
        **payback,
        "db_path": str(store.path) if store else None,
    }


def log_hems_event(coordinator: Any, event_type: str, payload: dict[str, Any]) -> None:
    store: PerformanceStore | None = getattr(coordinator, "_performance_store", None)
    if store is None:
        return
    store.log_event(
        ts=dt_util.utcnow().isoformat(),
        event_type=event_type,
        payload_json=json.dumps(payload, default=str),
    )
