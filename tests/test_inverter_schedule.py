"""Compiling Fox Plant's schedule into the EVO Mode Scheduler payload."""

import pytest

from custom_components.foxess_plant.inverter_schedule import (
    MAX_BASELINE_SLOTS,
    InverterScheduleError,
    InverterSlot,
    compile_inverter_schedule,
    expected_inverter_slots,
    schedule_differences,
    split_at_midnight,
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


def test_jit_slots_go_first() -> None:
    jit = InverterSlot(start="01:00", end="02:00", work_mode="force_charge", fd_soc=80, fd_pwr=3000)
    payload = _compile(
        _schedule(SchedulerSegmentConfig(start="00:00", end="06:00", work_mode="Back-up")), jit_slots=[jit]
    )
    assert [s["work_mode"] for s in payload["slots"]] == ["force_charge", "back_up"]


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
