"""Five-minute performance tick — sample, accumulate, midnight ledger commit."""

from __future__ import annotations

import json
import logging
from datetime import datetime
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
        coordinator._performance_day = local_date
        coordinator._performance_daily = new_daily_accumulator()
        coordinator._performance_recent_peak_kw = 0.0

    sample = collect_performance_sample(coordinator)
    await coordinator.async_update_performance_sensors(sample)

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
    store: PerformanceStore | None = coordinator._performance_store
    if store is None:
        return

    acc = coordinator._performance_daily or new_daily_accumulator()
    sample = collect_performance_sample(coordinator)
    cfg = coordinator.plant.performance

    pv_kwh = sample.pv_kwh_today
    solcast_kwh = sample.solcast_forecast_kwh_today
    peak = float(acc.get("peak_power_kw") or 0.0)
    peak_vs_rated = None
    if cfg.inverter_ac_limit_kw > 0 and peak > 0:
        peak_vs_rated = round(peak / cfg.inverter_ac_limit_kw * 100.0, 1)

    row = {
        "date": date,
        "pv_kwh": pv_kwh,
        "solcast_forecast_kwh": solcast_kwh,
        "forecast_accuracy_pct": _forecast_accuracy_pct(pv_kwh, solcast_kwh),
        "export_kwh": round(float(acc.get("export_kwh") or 0.0), 3),
        "import_kwh": round(float(acc.get("import_kwh") or 0.0), 3),
        "export_earnings_gbp": round(float(acc.get("export_earnings_gbp") or 0.0), 2),
        "import_spend_gbp": round(float(acc.get("import_spend_gbp") or 0.0), 2),
        "avoided_grid_cost_gbp": round(float(acc.get("avoided_grid_cost_gbp") or 0.0), 2),
        "clipping_loss_kwh": round(float(acc.get("clipping_loss_kwh") or 0.0), 3),
        "clipping_loss_valuation_gbp": round(float(acc.get("clipping_loss_valuation_gbp") or 0.0), 2),
        "net_daily_savings_gbp": net_daily_savings_gbp(acc),
        "peak_power_kw": round(peak, 2) if peak else None,
        "peak_vs_rated_pct": peak_vs_rated,
        "virtual_temp_min_c": acc.get("virtual_temp_min_c"),
        "virtual_temp_max_c": acc.get("virtual_temp_max_c"),
        "wind_correlation_note": None,
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
    store: PerformanceStore | None = getattr(coordinator, "_performance_store", None)
    cfg = coordinator.plant.performance
    today = coordinator._performance_day or dt_util.as_local(dt_util.now()).date().isoformat()
    acc = coordinator._performance_daily or {}
    ledger_today = store.get_daily_ledger(today) if store else None
    total_saved = store.sum_net_savings() if store else 0.0
    avg_90 = store.avg_net_savings_days(90) if store else None
    install_cost = cfg.system_install_cost_gbp
    payback_pct = None
    if install_cost and install_cost > 0:
        payback_pct = round(total_saved / install_cost * 100.0, 1)
    return {
        "enabled": cfg.enabled,
        "today": ledger_today or {
            "date": today,
            "net_daily_savings_gbp": net_daily_savings_gbp(acc) if acc else 0.0,
            "export_earnings_gbp": acc.get("export_earnings_gbp"),
            "import_spend_gbp": acc.get("import_spend_gbp"),
            "avoided_grid_cost_gbp": acc.get("avoided_grid_cost_gbp"),
        },
        "lifetime_saved_gbp": round(total_saved, 2),
        "payback_progress_pct": payback_pct,
        "avg_daily_savings_90d_gbp": round(avg_90, 2) if avg_90 is not None else None,
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
