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
    warning: bool = False,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "success": success,
        "message": message,
        "skipped": skipped,
        "warning": warning,
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
                f"Want {expected_wm!r} — inverter has {actual_wm!r}"
                if not wm_ok
                else f"{actual_wm!r}"
            ),
        ),
        _result(
            "min_soc",
            "Off-grid min",
            success=live.get("min_soc") == bundle.min_soc,
            message=(
                f"Want {bundle.min_soc}% — inverter has {live.get('min_soc')}%"
                if live.get("min_soc") != bundle.min_soc
                else f"{live.get('min_soc')}%"
            ),
        ),
        _result(
            "min_soc_on_grid",
            "System min",
            success=live.get("min_soc_on_grid") == bundle.min_soc_on_grid,
            message=(
                f"Want {bundle.min_soc_on_grid}% — inverter has {live.get('min_soc_on_grid')}%"
                if live.get("min_soc_on_grid") != bundle.min_soc_on_grid
                else f"{live.get('min_soc_on_grid')}%"
            ),
        ),
        _result(
            "max_soc",
            "System max",
            success=live.get("max_soc") == bundle.max_soc,
            message=(
                f"Want {bundle.max_soc}% — inverter has {live.get('max_soc')}%"
                if live.get("max_soc") != bundle.max_soc
                else f"{live.get('max_soc')}%"
            ),
        ),
    ]

    actual_rc = live.get("remote_control")
    rc_ok = _remote_control_matches(bundle, actual_rc)
    if bundle.force_charge:
        rc_msg = (
            "Force Charge"
            if rc_ok
            else f"Want Force Charge — inverter has {actual_rc!r}"
        )
    else:
        rc_msg = (
            "Disable"
            if rc_ok
            else f"Want Disable — inverter has {actual_rc!r}"
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
    """Poll live foxess_modbus entities until the bundle matches or timeout."""
    hass = coordinator.hass
    entity_map = coordinator.plant.entity_map
    keys = ("work_mode", "remote_control", *SOC_KEYS)
    loop = asyncio.get_running_loop()
    start = loop.time()
    last_rows: list[dict[str, Any]] = []

    while True:
        await async_refresh_entity_keys(hass, entity_map, keys)
        live = await read_live_schedule_state(coordinator)
        last_rows = _bundle_matches_live(coordinator, bundle, live)
        if all(row["success"] for row in last_rows):
            return last_rows
        if loop.time() - start >= timeout_s:
            elapsed = loop.time() - start
            for row in last_rows:
                if not row["success"] and row["message"]:
                    row["message"] = f"{row['message']} (after {elapsed:.0f}s)"
            return last_rows
        await asyncio.sleep(ENTITY_POLL_INTERVAL_S)


def _segment_window_label(seg: Any) -> str:
    return f"{seg.start}–{seg.end}"


def _segment_saved_summary(seg: Any) -> str:
    force = ", force charge" if seg.enable_force_charge else ""
    grid = " from grid" if seg.enable_charge_from_grid else ""
    return (
        f"{seg.work_mode}, SOC {seg.min_soc}/{seg.min_soc_on_grid}/{seg.max_soc}%"
        f"{force}{grid}"
    )


async def verify_saved_segments_on_inverter(
    coordinator: FoxESSPlantCoordinator,
    cfg: Any,
) -> list[dict[str, Any]]:
    """Prove whether each saved segment is live on the inverter right now."""
    from .schedule_runner import bundle_from_segment, resolve_active_segment

    results: list[dict[str, Any]] = []
    segments = list(cfg.segments or [])
    enabled = [(idx, seg) for idx, seg in enumerate(segments) if seg.enabled]

    if not cfg.enabled:
        return [
            _result(
                "scheduler_off",
                "HA scheduler",
                success=True,
                skipped=True,
                message="Scheduler disabled — timetable stored in Fox Plant only",
            )
        ]

    if not enabled:
        return [
            _result(
                "no_segments",
                "Schedule segments",
                success=True,
                skipped=True,
                message="No enabled segments — only remaining time mode applies",
            )
        ]

    active = resolve_active_segment(segments)
    any_active_proof = False

    for idx, seg in enabled:
        window = _segment_window_label(seg)
        saved = _segment_saved_summary(seg)
        if active is not None and seg.start == active.start and seg.end == active.end:
            any_active_proof = True
            expected = bundle_from_segment(seg)
            detail_rows = await verify_schedule_bundle(coordinator, expected)
            all_ok = all(row["success"] for row in detail_rows)
            results.append(
                _result(
                    f"segment_{idx}_proof",
                    f"Schedule {idx + 1} on inverter",
                    success=all_ok,
                    message=(
                        f"Active now ({window}) — live inverter matches saved segment"
                        if all_ok
                        else f"Active now ({window}) — inverter does NOT match saved segment"
                    ),
                )
            )
            for row in detail_rows:
                row["label"] = f"Schedule {idx + 1} · {row['label']}"
            results.extend(detail_rows)
        else:
            results.append(
                _result(
                    f"segment_{idx}_proof",
                    f"Schedule {idx + 1} on inverter",
                    success=False,
                    warning=True,
                    message=(
                        f"Not active now (outside {window}). Saved: {saved}. "
                        f"Fox Plant applies this via Modbus when {seg.start} starts."
                    ),
                )
            )

    if not any_active_proof:
        live = await read_live_schedule_state(coordinator)
        results.append(
            _result(
                "inverter_now",
                "Inverter right now",
                success=True,
                skipped=True,
                message=(
                    f"Remaining time: {live.get('work_mode')}, "
                    f"SOC {live.get('min_soc')}/{live.get('min_soc_on_grid')}/"
                    f"{live.get('max_soc')}%, Remote Control {live.get('remote_control')!r}"
                ),
            )
        )

    return results


async def verify_schedule_save(
    coordinator: FoxESSPlantCoordinator,
    cfg: Any,
    applied: ScheduleApplyBundle | None,
) -> list[dict[str, Any]]:
    """After save+apply, read back what HA pushed to the inverter."""
    results: list[dict[str, Any]] = [
        _result(
            "saved",
            "Saved in Fox Plant",
            success=True,
            skipped=True,
            message="Timetable on Home Assistant — Fox Plant applies each segment on the clock",
        ),
        _result(
            "ha_scheduler",
            "How it works",
            success=True,
            skipped=True,
            message=(
                "HA owns the schedule. Each minute Fox Plant pushes work mode, SOC, and "
                "Remote Control for the active window — not Fox app / 480xx charge periods."
            ),
        ),
    ]

    if applied is None:
        results.append(
            _result(
                "apply",
                "Apply now",
                success=True,
                skipped=True,
                message="Nothing pushed (scheduler off or plant control released)",
            )
        )
        return results

    results.extend(await verify_saved_segments_on_inverter(coordinator, cfg))
    return results
