"""Compile Fox Plant's schedule into the EVO's on-inverter Mode Scheduler.

The result is the payload for foxess_modbus's ``set_evo_schedule`` action. The inverter then runs the
schedule itself, so it keeps working if Home Assistant or Fox Plant stops. Register-level behaviour is
documented in foxess_modbus ``docs/evo/mode-scheduler.md``.

Pure functions only: no Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

# The inverter holds 7 slots plus the all-day "remaining" slot; keep one free for just-in-time
# SmartCharge / StormSafe slots.
MAX_INVERTER_SLOTS = 7
JIT_RESERVED_SLOTS = 1
MAX_BASELINE_SLOTS = MAX_INVERTER_SLOTS - JIT_RESERVED_SLOTS

SOC_MIN = 10
SOC_MAX = 100

_WORK_MODES = {
    "self use": "self_use",
    "feed-in first": "feed_in",
    "feed-in priority": "feed_in",
    "back-up": "back_up",
    "back up": "back_up",
}
REMAINING_WORK_MODES = frozenset({"self_use", "feed_in", "back_up"})


class InverterScheduleError(ValueError):
    """The schedule can't be represented on the inverter."""


@dataclass(frozen=True)
class InverterSlot:
    """One slot in foxess_modbus ``set_evo_schedule`` form."""

    start: str
    end: str
    work_mode: str
    min_soc: int = SOC_MIN
    max_soc: int = SOC_MAX
    fd_soc: int = SOC_MIN
    fd_pwr: int = 0

    def to_service(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "work_mode": self.work_mode,
            "min_soc": self.min_soc,
            "max_soc": self.max_soc,
            "fd_soc": self.fd_soc,
            "fd_pwr": self.fd_pwr,
        }


def _minutes(hhmm: str) -> int:
    parts = str(hhmm or "00:00").split(":")
    try:
        hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except ValueError as err:
        raise InverterScheduleError(f"Invalid time '{hhmm}'") from err
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise InverterScheduleError(f"Invalid time '{hhmm}'")
    return hour * 60 + minute


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def inverter_work_mode(fox_plant_mode: str) -> str:
    """Map a Fox Plant / foxess_modbus work mode label to the slot code name."""
    mode = _WORK_MODES.get(str(fox_plant_mode or "").strip().lower())
    if mode is None:
        raise InverterScheduleError(
            f"Work mode '{fox_plant_mode}' can't be used in an inverter schedule slot "
            "(supported: Self Use, Feed-in First, Back-up, or a force charge segment)"
        )
    return mode


def _soc(name: str, value: Any) -> int:
    try:
        soc = int(round(float(value)))
    except (TypeError, ValueError) as err:
        raise InverterScheduleError(f"{name} must be a number") from err
    if not SOC_MIN <= soc <= SOC_MAX:
        raise InverterScheduleError(f"{name} must be between {SOC_MIN} and {SOC_MAX}%, got {soc}")
    return soc


def split_at_midnight(start: str, end: str) -> list[tuple[str, str]]:
    """Inverter slots can't cross midnight; split e.g. 23:00–02:00 into 23:00–23:59 and 00:00–02:00."""
    start_m, end_m = _minutes(start), _minutes(end)
    if start_m == end_m:
        raise InverterScheduleError(f"Segment {start}–{end} has no length")
    if start_m < end_m:
        return [(_hhmm(start_m), _hhmm(end_m))]
    parts = [(_hhmm(start_m), "23:59")]
    if end_m > 0:
        parts.append(("00:00", _hhmm(end_m)))
    return parts


def slots_from_segment(segment: Any, *, default_force_power_w: int) -> list[InverterSlot]:
    """Turn one Fox Plant schedule segment (SchedulerSegmentConfig-like) into inverter slots."""
    if getattr(segment, "enable_force_charge", False):
        cut_off = _soc("Force charge target SoC", getattr(segment, "max_soc", SOC_MAX))
        power = getattr(segment, "force_charge_power_w", None) or default_force_power_w
        template = InverterSlot(
            start="", end="", work_mode="force_charge", fd_soc=cut_off, fd_pwr=int(power), max_soc=SOC_MAX
        )
    else:
        min_soc = _soc("Min SoC (on grid)", getattr(segment, "min_soc_on_grid", SOC_MIN))
        max_soc = _soc("Max SoC", getattr(segment, "max_soc", SOC_MAX))
        if min_soc > max_soc:
            raise InverterScheduleError(f"Min SoC ({min_soc}%) is above Max SoC ({max_soc}%)")
        template = InverterSlot(
            start="",
            end="",
            work_mode=inverter_work_mode(getattr(segment, "work_mode", "Self Use")),
            min_soc=min_soc,
            max_soc=max_soc,
        )
    return [replace(template, start=start, end=end) for start, end in split_at_midnight(segment.start, segment.end)]


def compile_inverter_schedule(
    plant_schedule: Any,
    *,
    remaining_min_soc: int,
    remaining_max_soc: int,
    default_force_power_w: int,
    jit_slots: list[InverterSlot] | None = None,
) -> dict[str, Any]:
    """Build the ``set_evo_schedule`` payload (without ``inverter``) for a PlantScheduleConfig-like object.

    Just-in-time slots (SmartCharge / StormSafe) go first so they take priority over the baseline.
    """
    jit = list(jit_slots or [])
    baseline: list[InverterSlot] = []
    for segment in getattr(plant_schedule, "segments", []) or []:
        if getattr(segment, "enabled", True):
            baseline.extend(slots_from_segment(segment, default_force_power_w=default_force_power_w))

    if len(baseline) > MAX_BASELINE_SLOTS:
        raise InverterScheduleError(
            f"The schedule needs {len(baseline)} inverter slots (segments crossing midnight count twice) but "
            f"at most {MAX_BASELINE_SLOTS} are available ({JIT_RESERVED_SLOTS} is kept for SmartCharge / StormSafe)"
        )
    if len(jit) + len(baseline) > MAX_INVERTER_SLOTS:
        raise InverterScheduleError(f"At most {MAX_INVERTER_SLOTS} inverter slots, got {len(jit) + len(baseline)}")

    remaining_mode = inverter_work_mode(getattr(plant_schedule, "remaining_work_mode", "Self Use"))
    remaining_min = _soc("Remaining-time min SoC", remaining_min_soc)
    remaining_max = _soc("Remaining-time max SoC", remaining_max_soc)
    if remaining_min > remaining_max:
        remaining_min = remaining_max

    return {
        "enabled": bool(getattr(plant_schedule, "enabled", True)),
        "slots": [slot.to_service() for slot in [*jit, *baseline]],
        "remaining": {"work_mode": remaining_mode, "min_soc": remaining_min, "max_soc": remaining_max},
    }
