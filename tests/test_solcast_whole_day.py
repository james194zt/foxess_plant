"""Today's Solcast total comes from all of today's polls, not just the latest (which starts at its fetch time)."""

from datetime import timedelta

from homeassistant.util import dt as dt_util

from custom_components.foxess_plant.solcast_forecast_metrics import (
    compute_forecast_metrics,
    whole_day_forecast_metrics,
)


def _rows(start, count: int, kw: float) -> list[dict]:
    return [
        {"period_start": (start + timedelta(minutes=30 * i)).isoformat(), "pv_estimate": kw} for i in range(count)
    ]


def test_whole_day_total_includes_periods_before_the_latest_poll() -> None:
    today = dt_util.start_of_local_day()
    morning = _rows(today + timedelta(hours=8), 8, 2.0)  # 08:00–12:00 at 2 kW = 8 kWh
    afternoon = _rows(today + timedelta(hours=12), 8, 1.0)  # 12:00–16:00 at 1 kW = 4 kWh
    latest_poll_only = compute_forecast_metrics(None, afternoon)
    merged = whole_day_forecast_metrics(morning + afternoon)
    assert merged["forecast_today_kwh"] == 12.0
    assert latest_poll_only["forecast_today_kwh"] < merged["forecast_today_kwh"]
    assert merged["peak_forecast_today_w"] == 2000.0


def test_rows_smartcharge_estimated_are_left_out() -> None:
    today = dt_util.start_of_local_day()
    rows = _rows(today + timedelta(hours=8), 2, 2.0) + [
        {**r, "estimated": True} for r in _rows(today + timedelta(hours=9), 2, 3.0)
    ]
    assert whole_day_forecast_metrics(rows)["forecast_today_kwh"] == 2.0


def test_nothing_for_today_leaves_the_poll_figures_alone() -> None:
    tomorrow = dt_util.start_of_local_day() + timedelta(days=1, hours=8)
    assert whole_day_forecast_metrics(_rows(tomorrow, 4, 1.0)) == {}
