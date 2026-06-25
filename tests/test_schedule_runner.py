"""Tests for HA schedule runner time resolution."""

from datetime import datetime

from custom_components.foxess_plant.models import SchedulerSegmentConfig
from custom_components.foxess_plant.schedule_runner import (
    resolve_active_segment,
    time_in_segment_range,
)


def test_time_in_segment_same_day():
    when = datetime(2026, 5, 28, 12, 30)
    assert time_in_segment_range("09:00", "17:00", when) is True
    assert time_in_segment_range("13:00", "17:00", when) is False


def test_time_in_segment_overnight():
    when = datetime(2026, 5, 28, 23, 30)
    assert time_in_segment_range("23:00", "23:50", when) is True
    when_late = datetime(2026, 5, 28, 0, 15)
    assert time_in_segment_range("23:00", "06:00", when_late) is True


def test_resolve_active_segment_first_match():
    segments = [
        SchedulerSegmentConfig(enabled=True, start="09:00", end="12:00", work_mode="Self Use"),
        SchedulerSegmentConfig(enabled=True, start="12:00", end="17:00", work_mode="Back-up"),
    ]
    active = resolve_active_segment(segments, datetime(2026, 5, 28, 10, 0))
    assert active is not None
    assert active.work_mode == "Self Use"
