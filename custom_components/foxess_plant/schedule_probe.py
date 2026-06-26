"""Temporary schedule write probe — test HA scheduler apply + live inverter read-back."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .entity_live import (
    ENTITY_POLL_TIMEOUT_S,
    async_poll_entity_key_live,
    async_read_entity_key_live,
    async_read_soc_live,
)
from .schedule_runner import ScheduleApplyBundle, apply_schedule_bundle, resolve_desired_bundle

_LOGGER = logging.getLogger(__name__)


def _timing_note(elapsed_s: float, attempts: int) -> str:
    return f"Live read-back after {elapsed_s:.1f}s ({attempts} poll(s), up to {ENTITY_POLL_TIMEOUT_S:.0f}s)."


def _pick_test_work_mode(current: str | None, options: list[str]) -> str | None:
    if not options:
        return None
    return next((opt for opt in options if opt != current), None)


def _pick_test_min_soc(current: int, mid: int, max_v: int) -> int | None:
    if current < min(mid, max_v):
        return current + 1
    if current > 10:
        return current - 1
    return None


async def _read_live_bundle_state(coordinator: Any) -> dict[str, Any]:
    hass = coordinator.hass
    entity_map = coordinator.plant.entity_map
    soc = await async_read_soc_live(hass, entity_map)
    return {
        "work_mode": await async_read_entity_key_live(hass, entity_map, "work_mode"),
        "remote_control": await async_read_entity_key_live(hass, entity_map, "remote_control"),
        "min_soc": soc.get("min_soc"),
        "min_soc_on_grid": soc.get("min_soc_on_grid"),
        "max_soc": soc.get("max_soc"),
        "virtual_max_soc": coordinator.plant.virtual_soc.max_soc,
    }


def _bundle_from_live(live: dict[str, Any], *, label: str = "snapshot") -> ScheduleApplyBundle:
    rc = live.get("remote_control")
    force = rc == "Force Charge"
    max_soc = live.get("virtual_max_soc")
    if max_soc is None:
        max_soc = live.get("max_soc")
    return ScheduleApplyBundle(
        work_mode=str(live.get("work_mode") or "Self Use"),
        min_soc=int(live.get("min_soc") or 10),
        min_soc_on_grid=int(live.get("min_soc_on_grid") or 10),
        max_soc=int(max_soc or 100),
        force_charge=force,
        charge_from_grid=force,
        source="restore",
        label=label,
    )


async def run_schedule_write_probe(coordinator: Any) -> dict[str, Any]:
    """Apply a test schedule bundle, verify live inverter read-back, restore prior state."""
    if not coordinator.plant.control_active:
        raise HomeAssistantError("Take plant control before running the schedule probe")

    if coordinator.plant.override.active and coordinator.plant.override.mode:
        raise HomeAssistantError(
            "StormSafe, SmartCharge, or another automation override is active — "
            "disarm it before testing the baseline schedule"
        )

    results: list[dict[str, Any]] = []
    saved_sig = getattr(coordinator, "_last_schedule_bundle_sig", None)
    desired_before = resolve_desired_bundle(coordinator)
    live_before = await _read_live_bundle_state(coordinator)
    restore_bundle = desired_before if desired_before is not None else _bundle_from_live(live_before)
    was_applying = getattr(coordinator, "_applying", False)
    coordinator._applying = True

    try:
        options = coordinator._entity_options("work_mode")
        target_mode = _pick_test_work_mode(live_before.get("work_mode"), options)
        if not target_mode:
            results.append(
                {
                    "id": "work_mode",
                    "name": "Work mode write + live read-back",
                    "status": "skip",
                    "notes": "No alternate work mode option available for test.",
                    "before": live_before.get("work_mode"),
                }
            )
        else:
            write_err: str | None = None
            min_v = int(live_before.get("min_soc") or 10)
            test_min = _pick_test_min_soc(
                min_v,
                int(live_before.get("min_soc_on_grid") or min_v),
                int(live_before.get("max_soc") or 100),
            )
            try:
                await coordinator._set_work_mode(target_mode)
            except Exception as err:
                write_err = str(err)

            read_ok = False
            after_mode: str | None = None
            poll_s = 0.0
            poll_attempts = 0
            if write_err is None:
                read_ok, after_mode, poll_s, poll_attempts = await async_poll_entity_key_live(
                    coordinator.hass,
                    coordinator.plant.entity_map,
                    "work_mode",
                    expected=target_mode,
                )
            results.append(
                {
                    "id": "work_mode",
                    "name": "Work mode write + live read-back",
                    "status": "pass" if write_err is None and read_ok else "fail",
                    "write_ok": write_err is None,
                    "read_back_ok": read_ok,
                    "before": live_before.get("work_mode"),
                    "attempted": target_mode,
                    "after": after_mode,
                    "error": write_err,
                    "notes": _timing_note(poll_s, poll_attempts) if write_err is None else None,
                }
            )

            if test_min is not None and test_min != min_v and write_err is None:
                after_soc = await async_read_soc_live(coordinator.hass, coordinator.plant.entity_map)
                min_ok = after_soc.get("min_soc") == test_min
                results.append(
                    {
                        "id": "min_soc",
                        "name": "Min SOC write + live read-back",
                        "status": "pass" if min_ok else "fail",
                        "write_ok": True,
                        "read_back_ok": min_ok,
                        "before": min_v,
                        "attempted": test_min,
                        "after": after_soc.get("min_soc"),
                        "notes": "Refreshed foxess_modbus number entities from inverter.",
                    }
                )
            else:
                results.append(
                    {
                        "id": "min_soc",
                        "name": "Min SOC write + live read-back",
                        "status": "skip",
                        "before": min_v,
                        "notes": "Could not pick a safe alternate min SOC for test.",
                    }
                )

        rc_before = live_before.get("remote_control")
        if rc_before not in (None, "Disable", "unknown", "unavailable", ""):
            results.append(
                {
                    "id": "remote_control",
                    "name": "Remote Control (unchanged during probe)",
                    "status": "skip",
                    "before": rc_before,
                    "notes": "Remote Control was active — probe did not toggle force charge.",
                }
            )
        else:
            after_rc = await async_read_entity_key_live(
                coordinator.hass, coordinator.plant.entity_map, "remote_control"
            )
            rc_ok = after_rc in ("Disable", None, "unknown", "unavailable", "")
            results.append(
                {
                    "id": "remote_control",
                    "name": "Remote Control stays Disable",
                    "status": "pass" if rc_ok else "warn",
                    "read_back_ok": rc_ok,
                    "before": rc_before,
                    "after": after_rc,
                    "notes": "Schedule probe does not enable force charge.",
                }
            )
    finally:
        coordinator._applying = was_applying
        restore_status = "pass"
        restore_error: str | None = None
        try:
            await apply_schedule_bundle(coordinator, restore_bundle)
            coordinator._last_schedule_bundle_sig = saved_sig
        except Exception as err:
            restore_status = "fail"
            restore_error = str(err)
            _LOGGER.warning("Schedule probe restore failed: %s", err)
        results.append(
            {
                "id": "restore",
                "name": "Restore prior schedule state",
                "status": restore_status,
                "read_back_ok": restore_status == "pass",
                "attempted": restore_bundle.label,
                "error": restore_error,
                "notes": f"Re-applied {restore_bundle.work_mode} / SOC {restore_bundle.min_soc}%",
            }
        )

    passed = sum(1 for row in results if row.get("status") == "pass")
    failed = sum(1 for row in results if row.get("status") == "fail")
    skipped = sum(1 for row in results if row.get("status") == "skip")
    warned = sum(1 for row in results if row.get("status") == "warn")
    return {
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "warned": warned,
        },
        "tests": results,
        "restored": True,
    }
