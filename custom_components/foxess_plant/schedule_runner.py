"""HA-owned schedule runner — apply Fox-app-style segments via Modbus commands."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, time
from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

from .models import ChargePeriodConfig, SchedulerSegmentConfig
from .remote_control import is_remote_control_active, set_remote_control_mode
from .soc_limits import apply_soc_limits, read_soc_current

if TYPE_CHECKING:
    from .coordinator import FoxESSPlantCoordinator

_LOGGER = logging.getLogger(__name__)

SOURCE_SEGMENT = "segment"
SOURCE_REMAINING = "remaining"
SOURCE_OVERRIDE = "override"
SOURCE_LEGACY = "legacy"


@dataclass(frozen=True)
class ScheduleApplyBundle:
    """Modbus commands for one schedule state."""

    work_mode: str
    min_soc: int
    min_soc_on_grid: int
    max_soc: int
    force_charge: bool
    charge_from_grid: bool
    source: str = SOURCE_SEGMENT
    label: str = ""

    def signature(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def _parse_hhmm(value: str) -> time:
    parts = str(value or "00:00").split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return time(hour=hour, minute=minute)


def _minutes_since_midnight(value: time) -> int:
    return value.hour * 60 + value.minute


def time_in_segment_range(start: str, end: str, when: datetime) -> bool:
    """True when local time falls inside [start, end) with midnight wrap."""
    start_t = _parse_hhmm(start)
    end_t = _parse_hhmm(end)
    now_m = _minutes_since_midnight(when.time())
    start_m = _minutes_since_midnight(start_t)
    end_m = _minutes_since_midnight(end_t)
    if start_m == end_m:
        return False
    if start_m < end_m:
        return start_m <= now_m < end_m
    return now_m >= start_m or now_m < end_m


def resolve_active_segment(
    segments: list[SchedulerSegmentConfig],
    when: datetime | None = None,
) -> SchedulerSegmentConfig | None:
    """Return the first enabled segment covering ``when`` (local HA time)."""
    local = dt_util.as_local(when or dt_util.now())
    for segment in segments:
        if not segment.enabled:
            continue
        if time_in_segment_range(segment.start, segment.end, local):
            return segment
    return None


def bundle_from_segment(segment: SchedulerSegmentConfig) -> ScheduleApplyBundle:
    return ScheduleApplyBundle(
        work_mode=segment.work_mode,
        min_soc=segment.min_soc,
        min_soc_on_grid=segment.min_soc_on_grid,
        max_soc=segment.max_soc,
        force_charge=segment.enable_force_charge,
        charge_from_grid=segment.enable_charge_from_grid,
        source=SOURCE_SEGMENT,
        label=segment.label or f"{segment.start}–{segment.end}",
    )


def bundle_from_remaining(
    remaining_work_mode: str,
    *,
    min_soc: int,
    min_soc_on_grid: int,
    max_soc: int,
) -> ScheduleApplyBundle:
    return ScheduleApplyBundle(
        work_mode=remaining_work_mode,
        min_soc=min_soc,
        min_soc_on_grid=min_soc_on_grid,
        max_soc=max_soc,
        force_charge=False,
        charge_from_grid=False,
        source=SOURCE_REMAINING,
        label="remaining",
    )


def bundle_from_override_periods(
    periods: list[ChargePeriodConfig],
    *,
    target_max_soc: float | None,
    min_soc: int = 10,
    min_soc_on_grid: int = 10,
    work_mode: str = "Self Use",
    mode_label: str = "automation",
) -> ScheduleApplyBundle:
    """Map StormSafe / SmartCharge charge windows to instant Modbus commands."""
    active = next((p for p in periods if p.enable_force_charge), periods[0] if periods else None)
    force = bool(active and active.enable_force_charge)
    grid = bool(active and active.enable_charge_from_grid)
    max_v = int(round(target_max_soc)) if target_max_soc is not None else 100
    return ScheduleApplyBundle(
        work_mode=work_mode,
        min_soc=min_soc,
        min_soc_on_grid=min_soc_on_grid,
        max_soc=max_v,
        force_charge=force,
        charge_from_grid=grid,
        source=SOURCE_OVERRIDE,
        label=mode_label,
    )


def resolve_desired_bundle(coordinator: FoxESSPlantCoordinator) -> ScheduleApplyBundle | None:
    """Pick the schedule bundle Fox Plant should apply right now."""
    plant = coordinator.plant
    if not plant.control_active:
        return None

    if plant.override.active and plant.override.periods:
        target_max: float | None = None
        mode = plant.override.mode
        if mode == "storm":
            target_max = plant.storm_prep.target_max_soc
        elif mode == "smart_charge":
            sc = plant.smart_charge
            target_max = sc.target_max_soc if sc.target_max_soc is not None else sc.max_target_soc
        elif mode == "forecast":
            target_max = plant.forecast_prep.target_max_soc
        elif mode == "outage":
            target_max = plant.outage_prep.target_max_soc
        current = read_soc_current(coordinator.hass, plant.entity_map)
        return bundle_from_override_periods(
            plant.override.periods,
            target_max_soc=target_max,
            min_soc=current.get("min_soc", 10),
            min_soc_on_grid=current.get("min_soc_on_grid", 10),
            mode_label=mode or "override",
        )

    schedule = plant.plant_schedule
    if not schedule.enabled:
        return None

    segment = resolve_active_segment(schedule.segments) if schedule.segments else None
    if segment:
        return bundle_from_segment(segment)
    virtual_max = plant.virtual_soc.max_soc
    current = read_soc_current(coordinator.hass, plant.entity_map)
    max_soc = int(virtual_max) if virtual_max is not None else current.get("max_soc", 100)
    return bundle_from_remaining(
        schedule.remaining_work_mode,
        min_soc=current.get("min_soc", 10),
        min_soc_on_grid=current.get("min_soc_on_grid", 10),
        max_soc=max_soc,
    )


def _soc_bundle_needs_write(
    current: dict[str, int],
    bundle: ScheduleApplyBundle,
    *,
    emulate_max: bool,
) -> bool:
    """True when min/on-grid/max registers need a Modbus write for this bundle."""
    if current.get("min_soc") != bundle.min_soc:
        return True
    if current.get("min_soc_on_grid") != bundle.min_soc_on_grid:
        return True
    if emulate_max:
        return False
    return current.get("max_soc") != bundle.max_soc


async def apply_schedule_bundle(
    coordinator: FoxESSPlantCoordinator,
    bundle: ScheduleApplyBundle,
) -> None:
    """Write work mode, SOC limits, and remote control for one schedule bundle."""
    from .discovery import device_is_evo
    from .virtual_max_soc import emulate_max_soc

    plant = coordinator.plant
    entity_map = plant.entity_map
    emulate_max = emulate_max_soc(coordinator)

    if bundle.max_soc < 100 or emulate_max:
        plant.virtual_soc.max_soc = bundle.max_soc
        if emulate_max:
            plant.virtual_soc.hardware_max_supported = False

    current_soc = read_soc_current(coordinator.hass, entity_map)
    if _soc_bundle_needs_write(current_soc, bundle, emulate_max=emulate_max):
        try:
            await apply_soc_limits(
                coordinator.hass,
                entity_map,
                min_soc=bundle.min_soc,
                min_soc_on_grid=bundle.min_soc_on_grid,
                max_soc=bundle.max_soc,
                force_write=True,
                verify=False,
                emulate_max_soc=emulate_max,
                inverter_target=plant.inverter_target,
                device_id=plant.device_id,
                live_battery_soc=coordinator._entity_float("battery_soc"),
            )
        except Exception as err:
            _LOGGER.warning(
                "Schedule SOC apply failed for %s / %s (continuing with work mode): %s",
                bundle.source,
                bundle.label,
                err,
            )

    await coordinator._set_work_mode(bundle.work_mode)

    rc_entity = entity_map.get("remote_control")
    if rc_entity:
        live_rc = coordinator._entity_state("remote_control")
        if bundle.force_charge:
            if live_rc != "Force Charge":
                await set_remote_control_mode(coordinator.hass, entity_map, "Force Charge")
        elif is_remote_control_active(live_rc):
            await set_remote_control_mode(coordinator.hass, entity_map, "Disable")

    if device_is_evo(coordinator.hass, plant.device_id, entity_map):
        _LOGGER.info(
            "Applied HA schedule bundle (%s / %s): work_mode=%s max_soc=%s force_charge=%s",
            bundle.source,
            bundle.label,
            bundle.work_mode,
            bundle.max_soc,
            bundle.force_charge,
        )


async def apply_current_schedule_state(
    coordinator: FoxESSPlantCoordinator,
    *,
    force: bool = False,
) -> bool:
    """Apply the bundle for the current minute if it changed. Returns True when applied."""
    bundle = resolve_desired_bundle(coordinator)
    if bundle is None:
        return False
    signature = bundle.signature()
    last = getattr(coordinator, "_last_schedule_bundle_sig", None)
    if not force and signature == last:
        return False
    await apply_schedule_bundle(coordinator, bundle)
    coordinator._last_schedule_bundle_sig = signature
    return True
