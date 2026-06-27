"""Live inverter read-back after HA mode scheduler apply."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from .entity_live import (
    ENTITY_POLL_INTERVAL_S,
    async_read_entity_key_live,
    async_read_soc_live,
    async_refresh_entity_keys,
)
from .remote_control import is_remote_control_active
from .schedule_runner import ScheduleApplyBundle
from .soc_limits import SOC_KEYS
from .virtual_max_soc import resolve_work_mode_option

if TYPE_CHECKING:
    from .coordinator import FoxESSPlantCoordinator

_LOGGER = logging.getLogger(__name__)

_VERIFY_TIMEOUT_S = 15.0


async def read_live_schedule_state(coordinator: FoxESSPlantCoordinator) -> dict[str, Any]:
    hass = coordinator.hass
    entity_map = coordinator.plant.entity_map
    soc = await async_read_soc_live(hass, entity_map)
    return {
        "work_mode": await async_read_entity_key_live(hass, entity_map, "work_mode"),
        "remote_control": await async_read_entity_key_live(hass, entity_map, "remote_control"),
        "min_soc": soc.get("min_soc"),
        "min_soc_on_grid": soc.get("min_soc_on_grid"),
        "max_soc": soc.get("max_soc"),
    }


def _result(
    key: str,
    label: str,
    *,
    success: bool,
    message: str,
    skipped: bool = False,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "success": success,
        "message": message,
        "skipped": skipped,
    }


def _work_mode_matches(expected: str, actual: str | None, options: list[str]) -> bool:
    if actual is None:
        return False
    resolved = resolve_work_mode_option(expected, options)
    if actual == resolved:
        return True
    for alt in (expected, resolved):
        if alt in options and actual == alt:
            return True
    return actual == expected


def _remote_control_matches(bundle: ScheduleApplyBundle, actual: str | None) -> bool:
    if bundle.force_charge:
        return actual == "Force Charge"
    return not is_remote_control_active(actual)


def _bundle_matches_live(
    coordinator: FoxESSPlantCoordinator,
    bundle: ScheduleApplyBundle,
    live: dict[str, Any],
) -> list[dict[str, Any]]:
    options = coordinator._entity_options("work_mode")
    expected_wm = resolve_work_mode_option(bundle.work_mode, options)
    actual_wm = live.get("work_mode")
    wm_ok = _work_mode_matches(bundle.work_mode, actual_wm, options)

    rows = [
        _result(
            "work_mode",
            "Work mode",
            success=wm_ok,
            message=(
                f"Inverter reports {actual_wm!r}"
                if wm_ok
                else f"Expected {expected_wm!r}, inverter has {actual_wm!r}"
            ),
        ),
        _result(
            "min_soc",
            "Off-grid min",
            success=live.get("min_soc") == bundle.min_soc,
            message=(
                f"{live.get('min_soc')}%"
                if live.get("min_soc") == bundle.min_soc
                else f"Expected {bundle.min_soc}%, inverter has {live.get('min_soc')}%"
            ),
        ),
        _result(
            "min_soc_on_grid",
            "System min",
            success=live.get("min_soc_on_grid") == bundle.min_soc_on_grid,
            message=(
                f"{live.get('min_soc_on_grid')}%"
                if live.get("min_soc_on_grid") == bundle.min_soc_on_grid
                else (
                    f"Expected {bundle.min_soc_on_grid}%, "
                    f"inverter has {live.get('min_soc_on_grid')}%"
                )
            ),
        ),
        _result(
            "max_soc",
            "System max",
            success=live.get("max_soc") == bundle.max_soc,
            message=(
                f"{live.get('max_soc')}%"
                if live.get("max_soc") == bundle.max_soc
                else f"Expected {bundle.max_soc}%, inverter has {live.get('max_soc')}%"
            ),
        ),
    ]

    actual_rc = live.get("remote_control")
    rc_ok = _remote_control_matches(bundle, actual_rc)
    if bundle.force_charge:
        rc_msg = (
            "Force Charge"
            if rc_ok
            else f"Expected Force Charge, inverter has {actual_rc!r}"
        )
    else:
        rc_msg = (
            "Disable"
            if rc_ok
            else f"Expected Disable, inverter has {actual_rc!r}"
        )
    rows.append(
        _result(
            "remote_control",
            "Remote Control",
            success=rc_ok,
            message=rc_msg,
        )
    )
    return rows


async def verify_schedule_bundle(
    coordinator: FoxESSPlantCoordinator,
    bundle: ScheduleApplyBundle,
    *,
    timeout_s: float = _VERIFY_TIMEOUT_S,
) -> list[dict[str, Any]]:
    """Poll live foxess_modbus entities until the applied bundle matches or timeout."""
    hass = coordinator.hass
    entity_map = coordinator.plant.entity_map
    keys = ("work_mode", "remote_control", *SOC_KEYS)
    loop = asyncio.get_running_loop()
    start = loop.time()
    attempts = 0
    last_live: dict[str, Any] = {}
    last_rows: list[dict[str, Any]] = []

    while True:
        attempts += 1
        await async_refresh_entity_keys(hass, entity_map, keys)
        last_live = await read_live_schedule_state(coordinator)
        last_rows = _bundle_matches_live(coordinator, bundle, last_live)
        if all(row["success"] for row in last_rows):
            if attempts > 1:
                elapsed = loop.time() - start
                _LOGGER.debug(
                    "Schedule read-back OK after %.1fs (%s poll(s)) for %s / %s",
                    elapsed,
                    attempts,
                    bundle.source,
                    bundle.label,
                )
            return last_rows
        if loop.time() - start >= timeout_s:
            elapsed = loop.time() - start
            _LOGGER.warning(
                "Schedule read-back incomplete after %.1fs (%s poll(s)) for %s / %s: %s",
                elapsed,
                attempts,
                bundle.source,
                bundle.label,
                last_live,
            )
            for row in last_rows:
                if not row["success"] and row["message"]:
                    row["message"] = f"{row['message']} (after {elapsed:.0f}s live read-back)"
            return last_rows
        await asyncio.sleep(ENTITY_POLL_INTERVAL_S)
