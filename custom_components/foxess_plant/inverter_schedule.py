"""Compile Fox Plant's schedule into the EVO's on-inverter Mode Scheduler.

The result is the payload for foxess_modbus's ``set_evo_schedule`` action. The inverter then runs the
schedule itself, so it keeps working if Home Assistant or Fox Plant stops. Register-level behaviour is
documented in foxess_modbus ``docs/evo/mode-scheduler.md``.

Pure functions only: no Home Assistant imports.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
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


# Just-in-time slots go onto the inverter this long before their window, so a short HA or network hiccup
# around the start doesn't miss the charge.
JIT_LEAD = timedelta(minutes=30)


def window_slots(
    window: dict[str, Any] | None,
    *,
    now: datetime,
    work_mode: str,
    cut_off_soc: int | None,
    power_w: int,
    lead: timedelta = JIT_LEAD,
) -> list[InverterSlot]:
    """Force Charge / Force Discharge slots for a planned window, or [] when it isn't due yet or has finished.

    ``window`` is a SmartCharge plan window: local ``start``/``end`` (HH:MM) for the slot times and
    ``start_utc``/``end_utc`` (ISO) for timing. The inverter runs at ``power_w`` and stops at ``cut_off_soc``.
    """
    if not window or cut_off_soc is None:
        return []
    try:
        start_utc = datetime.fromisoformat(str(window["start_utc"]))
        end_utc = datetime.fromisoformat(str(window["end_utc"]))
    except (KeyError, TypeError, ValueError):
        return []
    if not start_utc - lead <= now < end_utc:
        return []
    cut_off = max(SOC_MIN, min(SOC_MAX, int(cut_off_soc)))
    template = InverterSlot(start="", end="", work_mode=work_mode, fd_soc=cut_off, fd_pwr=int(power_w))
    return [
        replace(template, start=start, end=end)
        for start, end in split_at_midnight(str(window.get("start")), str(window.get("end")))
    ]


def charge_window_slots(
    window: dict[str, Any] | None,
    *,
    now: datetime,
    target_soc: float | None,
    power_w: int,
    lead: timedelta = JIT_LEAD,
) -> list[InverterSlot]:
    """Force Charge slots for a planned charge window: charge at ``power_w``, stop at ``target_soc`` (rounded up)."""
    cut_off = math.ceil(float(target_soc)) if target_soc is not None else None
    return window_slots(window, now=now, work_mode="force_charge", cut_off_soc=cut_off, power_w=power_w, lead=lead)


# EVO model names are "EVO <battery kWh>-<inverter kW>-<variant>", e.g. EVO 10-5-H = 10 kWh battery, 5 kW inverter
_EVO_RATING = re.compile(r"^\s*EVO\s*\d+(?:\.\d+)?\s*-\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
MAX_SLOT_POWER_W = 12000  # foxess_modbus set_evo_schedule's fd_pwr limit


def evo_rated_power_w(model_name: str | None) -> int | None:
    """Inverter rating from an EVO model name, e.g. "EVO 10-5-H" -> 5000 W; None if it can't be read."""
    match = _EVO_RATING.match(str(model_name or ""))
    if not match:
        return None
    return min(MAX_SLOT_POWER_W, int(float(match.group(1)) * 1000))


def export_window_slots(
    window: dict[str, Any] | None,
    *,
    now: datetime,
    end_soc: float | None,
    floor_soc: float,
    power_w: int,
    lead: timedelta = JIT_LEAD,
) -> list[InverterSlot]:
    """Force Discharge slots for a planned export window: stop at the plan's end SoC (rounded down), never
    below ``floor_soc`` (SmartCharge's export floor).

    Hardware-tested: a Force Discharge slot's power caps the inverter's TOTAL output (house + export), with
    the battery making up what solar doesn't. If it's lower than the house load, the house imports from the
    grid. So pass the inverter's rating (e.g. 5 kW on an EVO 10-5-H) as ``power_w``: the house is always covered first, and the
    cut-off still stops the export at the planned level.
    """
    if end_soc is None:
        return []
    cut_off = max(math.ceil(float(floor_soc)), math.floor(float(end_soc)))
    return window_slots(window, now=now, work_mode="force_discharge", cut_off_soc=cut_off, power_w=power_w, lead=lead)


# StormSafe holds the battery with a rolling slot: long enough to cover HA being down for a while, short
# enough that the inverter goes back to normal on its own if HA never returns.
STORM_HOLD = timedelta(hours=3)
STORM_EXTEND_BELOW = timedelta(hours=2)


def storm_hold_slots(
    *, now_local: datetime, target_soc: float, power_w: int, length: timedelta = STORM_HOLD
) -> tuple[list[InverterSlot], datetime]:
    """Force Charge slots from now for ``length``: charge to ``target_soc`` and hold it there.

    Returns the slots and when they end (local time).
    """
    start = now_local.replace(second=0, microsecond=0)
    end = start + length
    cut_off = max(SOC_MIN, min(SOC_MAX, math.ceil(float(target_soc))))
    template = InverterSlot(start="", end="", work_mode="force_charge", fd_soc=cut_off, fd_pwr=int(power_w))
    if end.date() == start.date():
        spans = [(_hhmm(start.hour * 60 + start.minute), _hhmm(end.hour * 60 + end.minute))]
    else:
        # Stop at 23:59 and carry on from 00:00 (inverter slots can't cross midnight)
        spans = [(_hhmm(start.hour * 60 + start.minute), "23:59")]
        if end.hour or end.minute:
            spans.append(("00:00", _hhmm(end.hour * 60 + end.minute)))
    return [replace(template, start=s, end=e) for s, e in spans], end


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

    slots = [*jit, *baseline]
    return {
        # Only switch the inverter's Mode Scheduler on when there's something to schedule. With it off the
        # inverter follows its normal work mode (49203), so work mode changes keep working.
        "enabled": bool(getattr(plant_schedule, "enabled", True)) and bool(slots),
        "slots": [slot.to_service() for slot in slots],
        "remaining": {"work_mode": remaining_mode, "min_soc": remaining_min, "max_soc": remaining_max},
    }


_COMPARED_FIELDS = ("start", "end", "work_mode", "min_soc", "max_soc", "fd_soc", "fd_pwr")


def expected_inverter_slots(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """The enabled slots the inverter should hold for a payload: its slots, then the all-day remaining slot."""
    remaining = payload["remaining"]
    filler = InverterSlot(
        start="00:00",
        end="23:59",
        work_mode=remaining["work_mode"],
        min_soc=remaining["min_soc"],
        max_soc=remaining["max_soc"],
    ).to_service()
    return [{field: slot[field] for field in _COMPARED_FIELDS} for slot in [*payload["slots"], filler]]


def schedule_differences(payload: dict[str, Any], inverter: dict[str, Any]) -> list[str]:
    """Compare a compiled payload with foxess_modbus ``get_evo_schedule``'s response. Empty means in sync."""
    differences: list[str] = []
    if bool(inverter.get("enabled")) != bool(payload["enabled"]):
        differences.append(f"Mode Scheduler is {'on' if inverter.get('enabled') else 'off'} on the inverter")
    actual = [
        {field: slot.get(field) for field in _COMPARED_FIELDS}
        for slot in inverter.get("slots") or []
        if slot.get("enabled")
    ]
    expected = expected_inverter_slots(payload)
    if actual != expected:
        differences.append(f"slots differ: inverter has {actual}, Fox Plant expects {expected}")
    return differences
