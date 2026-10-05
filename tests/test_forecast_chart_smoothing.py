"""Forecast chart lines are drawn through period midpoints, and statistics are asked for by period name."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from custom_components.foxess_plant.solcast_forecast_chart import _kw_at_or_after, _kw_at_time
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
