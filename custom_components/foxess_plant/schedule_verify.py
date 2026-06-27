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
from .models import ChargePeriodConfig
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


def _period_label(period: ChargePeriodConfig | dict[str, Any], slot: int) -> str:
    data = period.to_dict() if isinstance(period, ChargePeriodConfig) else period
    if not data.get("enable_force_charge"):
        return f"Period {slot}: disabled"
    grid = " from grid" if data.get("enable_charge_from_grid") else ""
    return f"Period {slot}: {data.get('start')}–{data.get('end')} force charge{grid}"


def _charge_periods_match(
    coordinator: FoxESSPlantCoordinator,
    expected: list[ChargePeriodConfig],
    actual: list[dict[str, Any]],
) -> bool:
    desired = [p.to_dict() for p in expected]
    return not coordinator._compute_drift(desired, actual)


async def verify_charge_periods_on_inverter(
    coordinator: FoxESSPlantCoordinator,
    expected: list[ChargePeriodConfig],
    *,
    timeout_s: float = _VERIFY_TIMEOUT_S,
) -> list[dict[str, Any]]:
    """Poll foxess_modbus charge-period entities until they match saved windows."""
    loop = asyncio.get_running_loop()
    start = loop.time()
    last_actual: list[dict[str, Any]] = []
    matched = False

    while True:
        await coordinator._refresh_charge_period_entities()
        last_actual = coordinator._read_actual_periods()
        matched = _charge_periods_match(coordinator, expected, last_actual)
        if matched:
            break
        if loop.time() - start >= timeout_s:
            break
        await asyncio.sleep(ENTITY_POLL_INTERVAL_S)

    summary_ok = matched
    elapsed = loop.time() - start
    rows: list[dict[str, Any]] = [
        _result(
            "charge_periods",
            "Charge periods on inverter (480xx)",
            success=summary_ok,
            message=(
                "Live read-back matches saved force-charge windows"
                if summary_ok
                else f"Inverter charge periods do not match saved schedule (after {elapsed:.0f}s)"
            ),
        )
    ]

    for idx in range(2):
        want = expected[idx] if idx < len(expected) else ChargePeriodConfig()
        got = last_actual[idx] if idx < len(last_actual) else {}
        slot = idx + 1
        if not want.enable_force_charge and not got.get("enable_force_charge"):
            rows.append(
                _result(
                    f"charge_period_{slot}",
                    f"Period {slot}",
                    success=True,
                    skipped=True,
                    message="Disabled",
                )
            )
            continue
        force_ok = bool(want.enable_force_charge) == bool(got.get("enable_force_charge"))
        grid_ok = bool(want.enable_charge_from_grid) == bool(got.get("enable_charge_from_grid"))
        start_ok = (
            not want.enable_force_charge
            or coordinator._normalize_period_time(want.start)
            == coordinator._normalize_period_time(got.get("start"))
        )
        end_ok = (
            not want.enable_force_charge
            or coordinator._normalize_period_time(want.end)
            == coordinator._normalize_period_time(got.get("end"))
        )
        ok = force_ok and grid_ok and start_ok and end_ok
        want_msg = _period_label(want, slot)
        got_msg = _period_label(got, slot)
        rows.append(
            _result(
                f"charge_period_{slot}",
                f"Period {slot} (480xx)",
                success=ok,
                message=(
                    want_msg
                    if ok
                    else f"Want {want_msg} — inverter has {got_msg}"
                ),
            )
        )
    return rows


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


def _same_segment(a: Any, b: Any) -> bool:
    return a.start == b.start and a.end == b.end


async def verify_saved_segments_on_inverter(
    coordinator: FoxESSPlantCoordinator,
    cfg: Any,
) -> list[dict[str, Any]]:
    """Read live work mode / SOC when a segment is active right now."""
    from .schedule_runner import bundle_from_segment, resolve_active_segment

    results: list[dict[str, Any]] = []
    segments = list(cfg.segments or [])
    enabled = [(idx, seg) for idx, seg in enumerate(segments) if seg.enabled]

    if not cfg.enabled or not enabled:
        return results

    active = resolve_active_segment(segments)
    if active is None:
        return results

    for idx, seg in enabled:
        if not _same_segment(seg, active):
            continue
        window = _segment_window_label(seg)
        expected = bundle_from_segment(seg)
        detail_rows = await verify_schedule_bundle(coordinator, expected)
        all_ok = all(row["success"] for row in detail_rows)
        results.append(
            _result(
                f"segment_{idx}_live",
                f"Active segment · work mode & SOC",
                success=all_ok,
                message=(
                    f"Schedule {idx + 1} active now ({window}) — live values match"
                    if all_ok
                    else f"Schedule {idx + 1} active now ({window}) — live values do NOT match"
                ),
            )
        )
        for row in detail_rows:
            row["label"] = f"Active segment · {row['label']}"
        results.extend(detail_rows)
        break

    return results


async def verify_schedule_save(
    coordinator: FoxESSPlantCoordinator,
    cfg: Any,
    applied: ScheduleApplyBundle | None,
    baseline: list[ChargePeriodConfig],
    charge_write: dict[str, Any],
) -> list[dict[str, Any]]:
    """After save+apply, prove charge periods (480xx) and active segment on inverter."""
    results: list[dict[str, Any]] = [
        _result(
            "saved",
            "Saved in Fox Plant",
            success=True,
            skipped=True,
            message="Timetable stored on Home Assistant",
        )
    ]

    if charge_write.get("skipped"):
        results.append(
            _result(
                "charge_periods_write",
                "Write charge periods (480xx)",
                success=False,
                warning=True,
                message=charge_write.get("error") or "Charge period entities not available",
            )
        )
    elif not charge_write.get("success"):
        results.append(
            _result(
                "charge_periods_write",
                "Write charge periods (480xx)",
                success=False,
                message=charge_write.get("error") or "foxess_modbus update_all_charge_periods failed",
            )
        )
    else:
        results.append(
            _result(
                "charge_periods_write",
                "Write charge periods (480xx)",
                success=True,
                message="Sent to inverter via foxess_modbus update_all_charge_periods",
            )
        )
        results.extend(await verify_charge_periods_on_inverter(coordinator, baseline))

    if applied is None:
        results.append(
            _result(
                "apply",
                "Apply work mode / SOC now",
                success=True,
                skipped=True,
                message="Nothing pushed (scheduler off or plant control released)",
            )
        )
        return results

    active = None
    if cfg.enabled and cfg.segments:
        from .schedule_runner import resolve_active_segment

        active = resolve_active_segment(cfg.segments)

    if active is None:
        enabled_segments = [seg for seg in (cfg.segments or []) if seg.enabled]
        if enabled_segments:
            results.append(
                _result(
                    "segment_timing",
                    "Work mode / SOC timing",
                    success=True,
                    skipped=True,
                    warning=True,
                    message=(
                        "No segment active right now — work mode and SOC apply on the "
                        "minute tick when each window starts. Charge periods above are "
                        "stored on the inverter for force-charge windows."
                    ),
                )
            )
    else:
        results.extend(await verify_saved_segments_on_inverter(coordinator, cfg))

    return results
