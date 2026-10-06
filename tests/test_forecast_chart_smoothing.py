"""Forecast chart lines are drawn through period midpoints, and statistics are asked for by period name."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from custom_components.foxess_plant.solcast_forecast_chart import (
    _kw_at_or_after,
    _kw_at_time,
    build_forecast_intraday_chart_for_range,
)
from custom_components.foxess_plant.websocket_api import _fetch_statistics_points

T0 = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)


def _rows(*kws: float) -> list[dict]:
    return [{"period_start": (T0 + timedelta(minutes=30 * i)).isoformat(), "pv_estimate": kw} for i, kw in enumerate(kws)]


def test_forecast_is_a_line_between_period_midpoints_not_steps() -> None:
    rows = _rows(1.0, 2.0, 3.0)
    assert _kw_at_time(rows, T0 + timedelta(minutes=15)) == 1.0  # first period's midpoint
    assert _kw_at_time(rows, T0 + timedelta(minutes=45)) == 2.0  # second midpoint
    assert abs(_kw_at_time(rows, T0 + timedelta(minutes=30)) - 1.5) < 1e-9  # boundary: halfway, no jump
    assert abs(_kw_at_time(rows, T0 + timedelta(minutes=60)) - 2.5) < 1e-9
    assert _kw_at_time(rows, T0 - timedelta(minutes=5)) is None


def test_future_slots_use_the_same_smooth_line() -> None:
    rows = _rows(1.0, 2.0)
    assert abs(_kw_at_or_after(rows, T0 + timedelta(minutes=30)) - 1.5) < 1e-9


def _day_rows(day_start: datetime, kw: float) -> list[dict]:
    return [
        {"period_start": (day_start + timedelta(hours=8, minutes=30 * i)).isoformat(), "pv_estimate": kw}
        for i in range(20)
    ]


def test_todays_line_uses_every_poll_not_just_the_latest() -> None:
    # 2026-10-06 morning: the newest stored poll didn't cover today, and its night-time 0 kW was repeated
    # across the whole day (a flat line). The earlier poll that did cover today must be used.
    day = datetime(2026, 10, 6, tzinfo=timezone.utc)
    covers_today = (day.timestamp() * 1000 - 6 * 3600_000, _day_rows(day, 2.0))  # fetched yesterday evening
    stale = (day.timestamp() * 1000 - 3600_000, _day_rows(day - timedelta(days=1), 0.0))  # newer, yesterday only
    as_of = day.timestamp() * 1000 + 6.5 * 3600_000
    pts = build_forecast_intraday_chart_for_range(
        snapshots=[covers_today, stale], day_start_ms=day.timestamp() * 1000, as_of_ms=as_of, include_future=True
    )
    noon = [p["v"] for p in pts if p["t"] == day.timestamp() * 1000 + 12 * 3600_000]
    assert noon == [2.0]
    # Nothing is invented where no poll has data (before 08:00 / after 18:00 here)
    assert all(day.timestamp() * 1000 + 8 * 3600_000 <= p["t"] < day.timestamp() * 1000 + 18 * 3600_000 for p in pts)


def test_statistics_are_requested_by_period_name() -> None:
    # HA reads the 5-minute table only for the exact string "5minute"; anything else came back hourly
    seen = {}

    def fake(hass, start, end, ids, period, units, types):
        seen.update(period=period, ids=ids, types=types)
        return {}

    with patch("homeassistant.components.recorder.statistics.statistics_during_period", fake):
        _fetch_statistics_points(None, T0, T0 + timedelta(hours=1), ["sensor.pv"], period="5minute")
        assert seen == {"period": "5minute", "ids": {"sensor.pv"}, "types": {"mean"}}
        _fetch_statistics_points(None, T0, T0 + timedelta(hours=1), ["sensor.pv"], period="hour")
        assert seen["period"] == "hour"
