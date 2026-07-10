"""SQLite period reports for performance ledger."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from ..smart_charge_analysis import reports_period_bounds
from .solar_analysis import payback_summary, solar_day_class_label


def _period_label(period: str, offset: int, start: datetime, end: datetime) -> str:
    if period == "week":
        return f"Week of {start.strftime('%d %b %Y')}"
    if period == "month":
        return start.strftime("%B %Y")
    if period == "year":
        return str(start.year)
    return f"{start.date().isoformat()} – {end.date().isoformat()}"


async def async_build_performance_report(
    coordinator: Any,
    *,
    period: str = "week",
    offset: int = 0,
) -> dict[str, Any]:
    """Aggregate daily_ledger rows for week/month/year."""
    store = getattr(coordinator, "_performance_store", None)
    if store is None:
        return {"error": "Performance store not initialised", "enabled": False}

    start, end, can_next = reports_period_bounds(period, offset)
    start_date = dt_util.as_local(start).date().isoformat()
    end_date = dt_util.as_local(end).date().isoformat()
    rows = store.list_ledger_between(start_date, end_date)
    summary = store.period_aggregate(start_date, end_date)

    cfg = coordinator.plant.performance
    total_saved = store.sum_net_savings()
    avg_90 = store.avg_net_savings_days(90)
    payback = payback_summary(
        total_saved_gbp=total_saved,
        install_cost_gbp=cfg.system_install_cost_gbp,
        avg_daily_savings_gbp=avg_90,
    )

    daily_chart = [
        {
            "date": row.get("date"),
            "pv_kwh": row.get("pv_kwh"),
            "net_savings_gbp": row.get("net_daily_savings_gbp"),
            "export_earnings_gbp": row.get("export_earnings_gbp"),
            "import_spend_gbp": row.get("import_spend_gbp"),
            "avoided_grid_cost_gbp": row.get("avoided_grid_cost_gbp"),
            "forecast_accuracy_pct": row.get("forecast_accuracy_pct"),
            "solar_day_class": row.get("solar_day_class"),
            "solar_day_class_label": solar_day_class_label(row.get("solar_day_class")),
        }
        for row in rows
    ]

    best_days = sorted(
        [r for r in rows if r.get("forecast_accuracy_pct") is not None],
        key=lambda r: float(r.get("forecast_accuracy_pct") or 0),
        reverse=True,
    )[:3]

    return {
        "enabled": cfg.enabled,
        "period": period,
        "offset": offset,
        "can_next": can_next,
        "period_label": _period_label(period, offset, dt_util.as_local(start), dt_util.as_local(end)),
        "start_date": start_date,
        "end_date": end_date,
        "summary": {**summary, **payback},
        "daily_chart": daily_chart,
        "highlights": {
            "best_forecast_days": [
                {
                    "date": r.get("date"),
                    "forecast_accuracy_pct": r.get("forecast_accuracy_pct"),
                    "insight_note": r.get("insight_note"),
                }
                for r in best_days
            ],
            "total_clipping_kwh": summary.get("clipping_loss_kwh"),
            "total_clipping_gbp": summary.get("clipping_loss_valuation_gbp"),
        },
    }
