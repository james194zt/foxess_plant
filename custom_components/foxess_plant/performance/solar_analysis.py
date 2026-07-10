"""Solar day classification and insight strings for performance reporting."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

SOLAR_CLASS_UNDER_FORECAST = "under_forecast"
SOLAR_CLASS_ON_TARGET = "on_target"
SOLAR_CLASS_OVER_FORECAST = "over_forecast"
SOLAR_CLASS_UNKNOWN = "unknown"


def classify_forecast_day(
    *,
    forecast_accuracy_pct: float | None,
    peak_vs_rated_pct: float | None = None,
) -> str:
    """Classify how actual PV compared to Solcast (cloud-mirror = under_forecast)."""
    if forecast_accuracy_pct is None:
        return SOLAR_CLASS_UNKNOWN
    if forecast_accuracy_pct > 110 or (peak_vs_rated_pct is not None and peak_vs_rated_pct > 100):
        return SOLAR_CLASS_UNDER_FORECAST
    if forecast_accuracy_pct < 90:
        return SOLAR_CLASS_OVER_FORECAST
    return SOLAR_CLASS_ON_TARGET


def solar_day_class_label(day_class: str | None) -> str:
    labels = {
        SOLAR_CLASS_UNDER_FORECAST: "Above forecast",
        SOLAR_CLASS_ON_TARGET: "On forecast",
        SOLAR_CLASS_OVER_FORECAST: "Below forecast",
        SOLAR_CLASS_UNKNOWN: "Unknown",
    }
    return labels.get(str(day_class or ""), "Unknown")


def build_daily_insight(
    *,
    forecast_accuracy_pct: float | None,
    peak_vs_rated_pct: float | None,
    solar_day_class: str,
    virtual_temp_min_c: float | None,
    virtual_temp_max_c: float | None,
    clipping_loss_kwh: float | None,
) -> str | None:
    """One-line insight for ledger and panel."""
    parts: list[str] = []
    if solar_day_class == SOLAR_CLASS_UNDER_FORECAST and forecast_accuracy_pct is not None:
        parts.append(f"{forecast_accuracy_pct:.0f}% of Solcast — likely cloud enhancement")
    elif solar_day_class == SOLAR_CLASS_OVER_FORECAST and forecast_accuracy_pct is not None:
        parts.append(f"{forecast_accuracy_pct:.0f}% of Solcast — persistent shade or haze")
    elif forecast_accuracy_pct is not None:
        parts.append(f"{forecast_accuracy_pct:.0f}% of Solcast")

    if peak_vs_rated_pct is not None and peak_vs_rated_pct > 100:
        parts.append(f"peak {peak_vs_rated_pct:.0f}% of inverter limit")

    if clipping_loss_kwh is not None and clipping_loss_kwh > 0.05:
        parts.append(f"clipping ~{clipping_loss_kwh:.1f} kWh")

    if (
        virtual_temp_min_c is not None
        and virtual_temp_max_c is not None
        and virtual_temp_max_c - virtual_temp_min_c >= 8
    ):
        parts.append(f"panel temp {virtual_temp_min_c:.0f}–{virtual_temp_max_c:.0f}°C")

    return " · ".join(parts) if parts else None


def estimate_break_even_date(
    *,
    total_saved_gbp: float,
    install_cost_gbp: float | None,
    avg_daily_savings_gbp: float | None,
    from_date: date | None = None,
) -> str | None:
    """Project calendar date when cumulative savings reach install cost."""
    if install_cost_gbp is None or install_cost_gbp <= 0:
        return None
    if avg_daily_savings_gbp is None or avg_daily_savings_gbp <= 0:
        return None
    remaining = float(install_cost_gbp) - float(total_saved_gbp)
    if remaining <= 0:
        return "paid_off"
    anchor = from_date or date.today()
    days_left = int(remaining / avg_daily_savings_gbp) + 1
    target = anchor + timedelta(days=days_left)
    return target.isoformat()


def payback_summary(
    *,
    total_saved_gbp: float,
    install_cost_gbp: float | None,
    avg_daily_savings_gbp: float | None,
) -> dict[str, Any]:
    progress_pct = None
    if install_cost_gbp and install_cost_gbp > 0:
        progress_pct = round(min(100.0, total_saved_gbp / install_cost_gbp * 100.0), 1)
    break_even = estimate_break_even_date(
        total_saved_gbp=total_saved_gbp,
        install_cost_gbp=install_cost_gbp,
        avg_daily_savings_gbp=avg_daily_savings_gbp,
    )
    return {
        "lifetime_saved_gbp": round(total_saved_gbp, 2),
        "payback_progress_pct": progress_pct,
        "break_even_date": break_even,
        "avg_daily_savings_90d_gbp": round(avg_daily_savings_gbp, 2) if avg_daily_savings_gbp else None,
    }
