"""Compiling Fox Plant's schedule into the EVO Mode Scheduler payload."""

from datetime import datetime, timezone

import pytest

from custom_components.foxess_plant.inverter_schedule import (
    MAX_BASELINE_SLOTS,
    InverterScheduleError,
    InverterSlot,
    charge_window_slots,
    compile_inverter_schedule,
    evo_rated_power_w,
    expected_inverter_slots,
    schedule_differences,
    split_at_midnight,
    storm_hold_slots,
)
from custom_components.foxess_plant.models import PlantScheduleConfig, SchedulerSegmentConfig


def _schedule(*segments: SchedulerSegmentConfig, remaining: str = "Self Use", enabled: bool = True):
    return PlantScheduleConfig(enabled=enabled, remaining_work_mode=remaining, segments=list(segments))


def _compile(schedule, **kwargs):
    return compile_inverter_schedule(
        schedule, remaining_min_soc=10, remaining_max_soc=100, default_force_power_w=6000, **kwargs
    )


def test_feed_in_segment_and_remaining() -> None:
    payload = _compile(
        _schedule(
            SchedulerSegmentConfig(start="20:15", end="21:45", work_mode="Feed-in First", min_soc_on_grid=30, max_soc=85)
        )
    )

    assert payload == {
        "enabled": True,
        "slots": [
            {"start": "20:15", "end": "21:45", "work_mode": "feed_in", "min_soc": 30, "max_soc": 85, "fd_soc": 10, "fd_pwr": 0}
        ],
        "remaining": {"work_mode": "self_use", "min_soc": 10, "max_soc": 100},
    }


def test_force_charge_segment_uses_max_soc_as_cut_off() -> None:
    payload = _compile(
        _schedule(SchedulerSegmentConfig(start="01:05", end="02:35", enable_force_charge=True, max_soc=95))
    )

    assert payload["slots"] == [
        {"start": "01:05", "end": "02:35", "work_mode": "force_charge", "min_soc": 10, "max_soc": 100, "fd_soc": 95, "fd_pwr": 6000}
    ]


def test_segment_crossing_midnight_is_split() -> None:
    assert split_at_midnight("23:00", "02:00") == [("23:00", "23:59"), ("00:00", "02:00")]
    assert split_at_midnight("23:00", "00:00") == [("23:00", "23:59")]

    payload = _compile(_schedule(SchedulerSegmentConfig(start="23:30", end="05:30", work_mode="Back-up")))
    assert [(s["start"], s["end"]) for s in payload["slots"]] == [("23:30", "23:59"), ("00:00", "05:30")]


def test_disabled_segments_are_skipped() -> None:
    payload = _compile(_schedule(SchedulerSegmentConfig(start="09:00", end="10:00", enabled=False)))
    assert payload["slots"] == []


def test_scheduler_stays_off_when_nothing_is_scheduled() -> None:
    # No slots: the inverter keeps following its normal work mode instead of an all-day Self Use slot
    assert _compile(_schedule())["enabled"] is False
    assert _compile(_schedule(SchedulerSegmentConfig(start="09:00", end="10:00")))["enabled"] is True


def test_jit_slots_go_first() -> None:
    jit = InverterSlot(start="01:00", end="02:00", work_mode="force_charge", fd_soc=80, fd_pwr=3000)
    payload = _compile(
        _schedule(SchedulerSegmentConfig(start="00:00", end="06:00", work_mode="Back-up")), jit_slots=[jit]
    )
    assert [s["work_mode"] for s in payload["slots"]] == ["force_charge", "back_up"]


_WINDOW = {
    "start": "01:00",
    "end": "04:30",
    "start_utc": "2026-10-06T00:00:00+00:00",  # 01:00 BST
    "end_utc": "2026-10-06T03:30:00+00:00",
}


def _utc(hhmm: str, day: int = 6) -> datetime:
    hour, minute = (int(x) for x in hhmm.split(":"))
    return datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (_utc("23:00", day=5), False),  # 01:00 BST is still 1 hour away
        (_utc("23:31", day=5), True),  # inside the 30 minute lead
        (_utc("02:00"), True),  # charging
        (_utc("03:30"), False),  # window over: remove the slot
    ],
)
def test_charge_window_slot_timing(now: datetime, expected: bool) -> None:
    slots = charge_window_slots(_WINDOW, now=now, target_soc=79.2, power_w=3000)
    assert bool(slots) is expected


def test_charge_window_slot_values() -> None:
    [slot] = charge_window_slots(_WINDOW, now=_utc("00:00"), target_soc=79.2, power_w=3000)
    assert slot == InverterSlot(start="01:00", end="04:30", work_mode="force_charge", fd_soc=80, fd_pwr=3000)


def test_charge_window_crossing_midnight_uses_two_slots() -> None:
    window = {**_WINDOW, "start": "23:30", "end": "02:00", "start_utc": "2026-10-05T22:30:00+00:00"}
    slots = charge_window_slots(window, now=_utc("22:45", day=5), target_soc=100, power_w=3000)
    assert [(s.start, s.end) for s in slots] == [("23:30", "23:59"), ("00:00", "02:00")]


def test_no_window_or_target_means_no_slot() -> None:
    assert charge_window_slots(None, now=_utc("02:00"), target_soc=80, power_w=3000) == []
    assert charge_window_slots(_WINDOW, now=_utc("02:00"), target_soc=None, power_w=3000) == []


@pytest.mark.parametrize(
    ("model", "watts"),
    [("EVO 10-5-H", 10000), ("EVO 6-5-H", 6000), ("evo10", 10000), ("H3-Pro-15.0", None), (None, None)],
)
def test_evo_rated_power(model, watts) -> None:
    assert evo_rated_power_w(model) == watts


def test_storm_hold_slot() -> None:
    now = datetime(2026, 10, 5, 14, 7, 42, tzinfo=timezone.utc)
    slots, until = storm_hold_slots(now_local=now, target_soc=99.5, power_w=6000)
    assert slots == [InverterSlot(start="14:07", end="17:07", work_mode="force_charge", fd_soc=100, fd_pwr=6000)]
    assert until == datetime(2026, 10, 5, 17, 7, tzinfo=timezone.utc)


def test_storm_hold_slot_across_midnight() -> None:
    now = datetime(2026, 10, 5, 22, 30, tzinfo=timezone.utc)
    slots, _ = storm_hold_slots(now_local=now, target_soc=100, power_w=6000)
    assert [(s.start, s.end) for s in slots] == [("22:30", "23:59"), ("00:00", "01:30")]


def test_too_many_baseline_slots_is_rejected() -> None:
    segments = [SchedulerSegmentConfig(start=f"{h:02d}:00", end=f"{h:02d}:30") for h in range(MAX_BASELINE_SLOTS + 1)]
    with pytest.raises(InverterScheduleError, match="at most 6"):
        _compile(_schedule(*segments))


@pytest.mark.parametrize(
    ("segment", "message"),
    [
        (SchedulerSegmentConfig(start="09:00", end="09:00"), "no length"),
        (SchedulerSegmentConfig(start="09:00", end="10:00", work_mode="Peak Shaving"), "can't be used"),
        (SchedulerSegmentConfig(start="09:00", end="10:00", min_soc_on_grid=60, max_soc=50), "above Max SoC"),
        (SchedulerSegmentConfig(start="09:00", end="10:00", min_soc_on_grid=5), "between 10 and 100"),
    ],
)
def test_invalid_segments_are_rejected(segment: SchedulerSegmentConfig, message: str) -> None:
    with pytest.raises(InverterScheduleError, match=message):
        _compile(_schedule(segment))


def _inverter_view(payload: dict, *, enabled: bool | None = None) -> dict:
    """What foxess_modbus get_evo_schedule returns after writing this payload (slots 1-8)."""
    slots = [{"enabled": True, **slot} for slot in expected_inverter_slots(payload)]
    blank = {"enabled": False, "start": "00:00", "end": "00:00", "work_mode": "self_use", "min_soc": 10,
             "max_soc": 100, "fd_soc": 10, "fd_pwr": 0}  # fmt: skip
    slots += [dict(blank) for _ in range(8 - len(slots))]
    return {"enabled": payload["enabled"] if enabled is None else enabled, "slots": slots}


def test_schedule_in_sync_with_inverter() -> None:
    payload = _compile(_schedule(SchedulerSegmentConfig(start="01:00", end="04:00", enable_force_charge=True, max_soc=90)))
    assert schedule_differences(payload, _inverter_view(payload)) == []


def test_schedule_drift_is_reported() -> None:
    payload = _compile(_schedule(SchedulerSegmentConfig(start="09:00", end="10:00", work_mode="Feed-in First")))

    switched_off = _inverter_view(payload, enabled=False)
    assert schedule_differences(payload, switched_off) == ["Mode Scheduler is off on the inverter"]

    edited = _inverter_view(payload)
    edited["slots"][0]["end"] = "11:00"  # e.g. edited in the Fox app
    assert schedule_differences(payload, edited)[0].startswith("slots differ")


def test_minute_runner_leaves_baseline_to_the_inverter() -> None:
    from types import SimpleNamespace

    from custom_components.foxess_plant.schedule_runner import resolve_desired_bundle

    plant = SimpleNamespace(
        control_active=True,
        override=SimpleNamespace(active=False, periods=[]),
        plant_schedule=_schedule(SchedulerSegmentConfig(start="00:00", end="23:59", work_mode="Feed-in First")),
    )
    on_inverter = SimpleNamespace(plant=plant, inverter_runs_schedule=lambda: True)
    assert resolve_desired_bundle(on_inverter) is None


def test_disabled_schedule_still_compiles_slots() -> None:
    payload = _compile(_schedule(SchedulerSegmentConfig(start="09:00", end="10:00"), enabled=False))
    assert payload["enabled"] is False
    assert len(payload["slots"]) == 1
