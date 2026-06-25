"""Apply FoxESS SOC limits via foxess_modbus number entities."""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .discovery import device_is_evo, resolve_uses_h3_pro_soc_block

_LOGGER = logging.getLogger(__name__)

SOC_KEYS = ("min_soc", "min_soc_on_grid", "max_soc")
SOC_DISPLAY_ORDER = ("min_soc", "min_soc_on_grid", "max_soc")
SOC_LABELS = {
    "min_soc": "Off-grid Min. SOC",
    "min_soc_on_grid": "System Min. SOC",
    "max_soc": "System Max. SOC",
}

# Physical holding registers: 46609=off-grid min, 46610=max, 46611=system min.
# EVO accepts FC6 single-register writes only; FC16 multi-register at 46609 fails IllegalAddress.
EVO_SOC_WRITE_ORDER = ("min_soc", "min_soc_on_grid", "max_soc")


@dataclass
class SocWriteResult:
    """Outcome of one SOC limit write (Fox app shows one row per limit)."""

    key: str
    label: str
    value: int
    success: bool
    message: str
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

_ILLEGAL_VALUE_HINT = (
    "Modbus rejected an SOC limit write (EVO/H3 Pro: 46609 off-grid min, 46610 max, 46611 system min). "
    "On EVO write all three limits as single registers in order: off-grid min, system min, then max. "
    "The inverter also requires off-grid min ≤ system min ≤ max. "
    "Disable FoxESS Modbus Remote Control and close the Fox app before saving."
)

_EVO_MAX_SOC_UNSUPPORTED = (
    "System max SOC cannot be changed on this EVO — Modbus register 46610 is read-only and "
    "Fox Cloud returns API 42015 (feature not supported). Off-grid min and system min were saved. "
    "Set system max in the Fox web portal installer settings, or cap charging using "
    "FoxESS Modbus charge periods / max charge current automations instead."
)

_EVO_MAX_SOC_BLOCKED_HINT = (
    "System max (register 46610) was rejected by the EVO inverter. Off-grid min and system min were saved. "
    "Fox Plant tries Fox Cloud MaxSoc and scheduler maxSoc when Modbus fails. "
    "If you see API 42015, this EVO does not expose system max via the Open API — use the Fox web portal "
    "(installer settings) or charge-period / max-current workarounds instead."
)

_VERIFY_FAIL_HINT = (
    "SOC limits did not read back from the inverter after save. "
    "Home Assistant may have reported success without the inverter accepting the values. "
    "Check the FoxESS Modbus number entities in Developer Tools — if those differ from "
    "the Fox app, the app may be showing cloud settings or locking changes."
)


def _coerce_soc(value: Any) -> int | None:
    if value is None or value in ("unknown", "unavailable"):
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def clamp_soc_values(
    min_soc: int,
    min_soc_on_grid: int,
    max_soc: int,
    *,
    soc_min_pct: int = 10,
) -> dict[str, int]:
    """Enforce 10–100% and min ≤ on-grid ≤ max."""
    min_v = max(soc_min_pct, min(100, int(min_soc)))
    mid_v = max(soc_min_pct, min(100, int(min_soc_on_grid)))
    max_v = max(soc_min_pct, min(100, int(max_soc)))
    if mid_v < min_v:
        mid_v = min_v
    if max_v < mid_v:
        max_v = mid_v
    return {
        "min_soc": min_v,
        "min_soc_on_grid": mid_v,
        "max_soc": max_v,
    }


def validate_soc_limits_for_write(
    min_soc: int,
    min_soc_on_grid: int,
    max_soc: int,
    *,
    soc_min_pct: int = 10,
    live_battery_soc: float | None = None,
    emulate_max_soc: bool = False,
) -> dict[str, int]:
    """Validate user SOC limits before Modbus writes; return clamped target or raise."""
    target = clamp_soc_values(min_soc, min_soc_on_grid, max_soc, soc_min_pct=soc_min_pct)
    errors: list[str] = []

    try:
        raw_min = int(min_soc)
        raw_mid = int(min_soc_on_grid)
        raw_max = int(max_soc)
    except (TypeError, ValueError):
        raise HomeAssistantError("SOC limits must be whole-number percentages.") from None

    if raw_min < soc_min_pct or raw_mid < soc_min_pct or raw_max < soc_min_pct:
        errors.append(f"All SOC limits must be at least {soc_min_pct}%.")
    if raw_min > 100 or raw_mid > 100 or raw_max > 100:
        errors.append("SOC limits cannot exceed 100%.")
    if raw_min > raw_mid:
        errors.append(
            f"Off-grid min ({raw_min}%) must be less than or equal to system min ({raw_mid}%)."
        )
    if raw_mid > raw_max:
        errors.append(
            f"System min ({raw_mid}%) must be less than or equal to system max ({raw_max}%)."
        )

    if not emulate_max_soc:
        battery_hint = _max_soc_battery_hint(live_battery_soc, raw_max)
        if battery_hint:
            errors.append(battery_hint)

    if errors:
        raise HomeAssistantError(" ".join(errors))
    return target


def compute_soc_write_sequence(
    target: dict[str, int],
    current: dict[str, Any],
) -> list[tuple[str, int]]:
    """Return SOC writes ordered so the inverter never sees an invalid triple."""
    t = clamp_soc_values(target["min_soc"], target["min_soc_on_grid"], target["max_soc"])
    cur: dict[str, int] = {}
    for key in SOC_KEYS:
        parsed = _coerce_soc(current.get(key))
        if parsed is not None:
            cur[key] = parsed

    if len(cur) < 3:
        return [(key, t[key]) for key in ("max_soc", "min_soc_on_grid", "min_soc")]

    seq: list[tuple[str, int]] = []
    state = dict(cur)

    def write(key: str, value: int) -> None:
        if state.get(key) != value:
            seq.append((key, value))
            state[key] = value

    if t["min_soc"] > state.get("min_soc_on_grid", t["min_soc"]):
        write("min_soc_on_grid", max(t["min_soc_on_grid"], t["min_soc"]))
    if t["min_soc_on_grid"] > state.get("max_soc", t["max_soc"]):
        write("max_soc", t["max_soc"])
    if t["max_soc"] < state.get("min_soc_on_grid", t["min_soc_on_grid"]):
        write("min_soc_on_grid", min(t["min_soc_on_grid"], t["max_soc"]))
    if t["min_soc_on_grid"] < state.get("min_soc", t["min_soc"]):
        write("min_soc", t["min_soc"])

    for key in ("max_soc", "min_soc_on_grid", "min_soc"):
        if t[key] > state.get(key, t[key]):
            write(key, t[key])
    for key in ("min_soc", "min_soc_on_grid", "max_soc"):
        if t[key] < state.get(key, t[key]):
            write(key, t[key])
    for key in ("max_soc", "min_soc_on_grid", "min_soc"):
        write(key, t[key])
    return seq


async def _refresh_soc_entity(hass: HomeAssistant, entity_map: dict[str, str], key: str) -> None:
    entity_id = entity_map.get(key)
    if entity_id:
        await hass.services.async_call(
            "homeassistant",
            "update_entity",
            {"entity_id": entity_id},
            blocking=True,
        )


async def _refresh_soc_entities(hass: HomeAssistant, entity_map: dict[str, str]) -> None:
    for key in SOC_KEYS:
        await _refresh_soc_entity(hass, entity_map, key)


def _read_soc_key(hass: HomeAssistant, entity_map: dict[str, str], key: str) -> int | None:
    entity_id = entity_map.get(key)
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    return _coerce_soc(state.state if state else None)


def read_soc_current(hass: HomeAssistant, entity_map: dict[str, str]) -> dict[str, int]:
    current: dict[str, int] = {}
    for key in SOC_KEYS:
        entity_id = entity_map.get(key)
        if not entity_id:
            continue
        state = hass.states.get(entity_id)
        parsed = _coerce_soc(state.state if state else None)
        if parsed is not None:
            current[key] = parsed
    return current


async def verify_soc_limits(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    target: dict[str, int],
) -> None:
    """Re-read number entities and confirm the inverter holds the requested limits."""
    await _refresh_soc_entities(hass, entity_map)
    await asyncio.sleep(0.35)
    current = read_soc_current(hass, entity_map)
    mismatches: list[str] = []
    for key in SOC_KEYS:
        want = target[key]
        got = current.get(key)
        if got is None:
            mismatches.append(f"{key}: no read-back")
        elif got != want:
            label = key.replace("_", " ")
            mismatches.append(f"{label} expected {want}% but inverter reports {got}%")
    if mismatches:
        raise HomeAssistantError(f"{_VERIFY_FAIL_HINT} {'; '.join(mismatches)}.")


def _max_soc_battery_hint(live_battery_soc: float | None, target_max: int) -> str | None:
    if live_battery_soc is None:
        return None
    try:
        live = int(math.ceil(float(live_battery_soc)))
    except (TypeError, ValueError):
        return None
    if 0 < live <= 100 and live > target_max:
        return (
            f"System max cannot be below the current battery level ({live}%). "
            "Discharge or wait for SOC to drop, then try again."
        )
    return None


def _format_soc_error(
    err: BaseException,
    *,
    key: str | None = None,
    target_max: int | None = None,
    live_battery_soc: float | None = None,
    evo_max_blocked: bool = False,
) -> str:
    message = str(err).strip()
    if not message or message.lower() == "unknown error":
        label = SOC_LABELS.get(key, key) if key else "SOC limit"
        message = (
            f"Failed to write {label}. Disable FoxESS Modbus Remote Control, "
            "close the Fox app, and try again."
        )
    if evo_max_blocked and key == "max_soc":
        return f"{_EVO_MAX_SOC_BLOCKED_HINT} Details: {message}"
    if key == "max_soc" and "IllegalValue" in message:
        battery_hint = _max_soc_battery_hint(live_battery_soc, target_max or 0)
        if battery_hint:
            return battery_hint
    if "IllegalValue" in message or "46609" in message or "46610" in message or "46611" in message:
        return f"{_ILLEGAL_VALUE_HINT} Details: {message}"
    return message


def _raise_soc_error(err: BaseException) -> None:
    raise HomeAssistantError(_format_soc_error(err)) from err


def _soc_result(
    key: str,
    value: int,
    *,
    success: bool,
    message: str,
    skipped: bool = False,
) -> SocWriteResult:
    return SocWriteResult(
        key=key,
        label=SOC_LABELS[key],
        value=value,
        success=success,
        message=message,
        skipped=skipped,
    )


async def _verify_soc_key(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    key: str,
    want: int,
) -> SocWriteResult:
    await _refresh_soc_entity(hass, entity_map, key)
    await asyncio.sleep(0.25)
    got = _read_soc_key(hass, entity_map, key)
    if got is None:
        return _soc_result(key, want, success=False, message="No read-back from inverter")
    if got == want:
        return _soc_result(key, want, success=True, message="Operation successful")
    return _soc_result(
        key,
        want,
        success=False,
        message=f"Inverter reports {got}% (expected {want}%)",
    )


def _build_soc_results(
    target: dict[str, int],
    outcomes: dict[str, SocWriteResult],
) -> list[dict[str, Any]]:
    """One Fox-app-style row per limit, in display order."""
    rows: list[dict[str, Any]] = []
    for key in SOC_DISPLAY_ORDER:
        if key in outcomes:
            rows.append(outcomes[key].to_dict())
        else:
            rows.append(
                _soc_result(
                    key,
                    target[key],
                    success=False,
                    message="Not written (a previous step failed)",
                ).to_dict()
            )
    return rows


async def _write_soc_number(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    key: str,
    value: int,
) -> None:
    entity_id = entity_map.get(key)
    if not entity_id:
        raise HomeAssistantError(
            f"SOC entity {key} is missing on the linked inverter. "
            "Reload FoxESS Plant after FoxESS Modbus has finished loading."
        )
    if not entity_id.startswith("number."):
        raise HomeAssistantError(
            f"SOC entity {entity_id} is not a number entity (writable). "
            "Reload FoxESS Plant to refresh entity discovery."
        )
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id, "value": value},
        blocking=True,
    )


async def _maybe_disable_remote_control_for_soc(
    hass: HomeAssistant,
    entity_map: dict[str, str],
) -> bool:
    """Disable active remote control so SOC block writes are not rejected."""
    from .remote_control import is_remote_control_active, set_remote_control_mode

    entity_id = entity_map.get("remote_control")
    if not entity_id:
        return False
    state = hass.states.get(entity_id)
    current = state.state if state else None
    if not is_remote_control_active(current):
        return False
    try:
        await set_remote_control_mode(hass, entity_map, "Disable")
        await asyncio.sleep(0.4)
        return True
    except HomeAssistantError as err:
        _LOGGER.debug("Remote Control disable before SOC write skipped: %s", err)
        return False


async def _maybe_clear_evo_remote_work_mode(hass: HomeAssistant, entity_map: dict[str, str]) -> bool:
    """Leave EVO remote-control work mode (49203=255) so SOC registers accept writes."""
    entity_id = entity_map.get("work_mode")
    if not entity_id:
        return False
    state = hass.states.get(entity_id)
    current = state.state if state else None
    if current not in ("Remote Control", "Force Charge", "Force Discharge"):
        return False
    try:
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": "Self Use"},
            blocking=True,
        )
        await asyncio.sleep(0.5)
        return True
    except HomeAssistantError as err:
        _LOGGER.debug("Work mode Self Use before SOC write skipped: %s", err)
        return False


async def _prepare_inverter_for_soc_writes(hass: HomeAssistant, entity_map: dict[str, str]) -> None:
    await _maybe_disable_remote_control_for_soc(hass, entity_map)
    await _maybe_clear_evo_remote_work_mode(hass, entity_map)


def _soc_targets_match(target: dict[str, int], current: dict[str, int]) -> bool:
    return all(current.get(key) == target[key] for key in SOC_KEYS)


async def _apply_contiguous_soc_writes(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    target: dict[str, int],
    *,
    live_battery_soc: float | None,
    verify: bool,
    device_id: str | None = None,
    emulate_max_soc: bool = False,
) -> list[dict[str, Any]]:
    """EVO/H3 Pro: FC6 writes for 46609, 46611, 46610 — always in min → system min → max order."""
    is_evo = device_is_evo(hass, device_id, entity_map)
    await _prepare_inverter_for_soc_writes(hass, entity_map)
    outcomes: dict[str, SocWriteResult] = {}
    write_failed = False
    write_order = (
        ("min_soc", "min_soc_on_grid") if emulate_max_soc else EVO_SOC_WRITE_ORDER
    )

    for key in write_order:
        value = target[key]
        if write_failed:
            outcomes[key] = _soc_result(
                key,
                value,
                success=False,
                message="Not written (a previous step failed)",
            )
            continue
        current = _read_soc_key(hass, entity_map, key)
        if current == value:
            outcomes[key] = _soc_result(
                key,
                value,
                success=True,
                message="Already set",
                skipped=True,
            )
            continue
        try:
            await _write_soc_number(hass, entity_map, key, value)
            if verify:
                outcomes[key] = await _verify_soc_key(hass, entity_map, key, value)
                if not outcomes[key].success and key == "max_soc":
                    battery_hint = _max_soc_battery_hint(live_battery_soc, value)
                    if battery_hint:
                        outcomes[key] = _soc_result(key, value, success=False, message=battery_hint)
                if not outcomes[key].success:
                    write_failed = True
            else:
                outcomes[key] = _soc_result(key, value, success=True, message="Operation successful")
        except Exception as err:
            msg = _format_soc_error(
                err,
                key=key,
                target_max=target["max_soc"] if key == "max_soc" else None,
                live_battery_soc=live_battery_soc,
                evo_max_blocked=is_evo and key == "max_soc" and "IllegalValue" in str(err),
            )
            outcomes[key] = _soc_result(key, value, success=False, message=msg)
            write_failed = True

    if emulate_max_soc:
        from .virtual_max_soc import virtual_max_soc_message

        outcomes["max_soc"] = _soc_result(
            "max_soc",
            target["max_soc"],
            success=True,
            message=virtual_max_soc_message(target["max_soc"]),
            skipped=True,
        )

    return _build_soc_results(target, outcomes)


async def apply_soc_limits(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    *,
    min_soc: int,
    min_soc_on_grid: int,
    max_soc: int,
    current: dict[str, Any] | None = None,
    force_write: bool = False,
    verify: bool = False,
    inverter_target: str | None = None,
    device_id: str | None = None,
    live_battery_soc: float | None = None,
    emulate_max_soc: bool = False,
) -> list[dict[str, Any]]:
    """Write min / on-grid / max SOC through foxess_modbus number entities."""
    target = validate_soc_limits_for_write(
        min_soc,
        min_soc_on_grid,
        max_soc,
        live_battery_soc=live_battery_soc,
        emulate_max_soc=emulate_max_soc,
    )

    if force_write or current is None:
        await _refresh_soc_entities(hass, entity_map)
        live_current = read_soc_current(hass, entity_map)
    else:
        live_current = {
            key: parsed
            for key in SOC_KEYS
            if (parsed := _coerce_soc(current.get(key))) is not None
        }

    uses_contiguous_soc = bool(
        resolve_uses_h3_pro_soc_block(hass, device_id, entity_map)
    )
    if uses_contiguous_soc:
        _LOGGER.info(
            "SOC write path: sequential FC6 46609→46611→46610 (min=%s system_min=%s max=%s)",
            target["min_soc"],
            target["min_soc_on_grid"],
            target["max_soc"],
        )
    else:
        _LOGGER.debug(
            "SOC write path: per-register number entities (device_id=%s, inverter=%s)",
            device_id,
            inverter_target,
        )

    if verify and _soc_targets_match(target, live_current) and not emulate_max_soc:
        outcomes = {
            key: _soc_result(
                key,
                target[key],
                success=True,
                message="Already set",
                skipped=True,
            )
            for key in SOC_DISPLAY_ORDER
        }
        return _build_soc_results(target, outcomes)

    if uses_contiguous_soc:
        return await _apply_contiguous_soc_writes(
            hass,
            entity_map,
            target,
            live_battery_soc=live_battery_soc,
            verify=verify,
            device_id=device_id,
            emulate_max_soc=emulate_max_soc,
        )

    sequence_current = dict(live_current)
    if emulate_max_soc and sequence_current:
        sequence_current["max_soc"] = target["max_soc"]
    sequence = compute_soc_write_sequence(target, sequence_current)
    if emulate_max_soc:
        sequence = [(key, value) for key, value in sequence if key != "max_soc"]
    if not sequence and verify:
        outcomes = {
            key: _soc_result(
                key,
                target[key],
                success=True,
                message="Already set",
                skipped=True,
            )
            for key in SOC_DISPLAY_ORDER
        }
        return _build_soc_results(target, outcomes)

    # H1 / legacy inverters — ordered per-register writes.
    await _prepare_inverter_for_soc_writes(hass, entity_map)
    outcomes: dict[str, SocWriteResult] = {}
    errors: dict[str, str] = {}
    write_failed = False

    for key, value in sequence:
        if write_failed:
            break
        entity_id = entity_map.get(key)
        if not entity_id:
            raise HomeAssistantError(
                f"SOC entity {key} is missing on the linked inverter. "
                "Reload FoxESS Plant after FoxESS Modbus has finished loading."
            )
        if not entity_id.startswith("number."):
            raise HomeAssistantError(
                f"SOC entity {entity_id} is not a number entity (writable). "
                "Reload FoxESS Plant to refresh entity discovery."
            )
        try:
            await _write_soc_number(hass, entity_map, key, value)
            if verify:
                outcomes[key] = await _verify_soc_key(hass, entity_map, key, value)
                if not outcomes[key].success and key == "max_soc":
                    battery_hint = _max_soc_battery_hint(live_battery_soc, value)
                    if battery_hint:
                        outcomes[key] = _soc_result(key, value, success=False, message=battery_hint)
                if not outcomes[key].success:
                    errors[key] = outcomes[key].message
                    write_failed = True
            else:
                outcomes[key] = _soc_result(key, value, success=True, message="Operation successful")
        except Exception as err:
            msg = _format_soc_error(
                err,
                key=key,
                target_max=target["max_soc"] if key == "max_soc" else None,
                live_battery_soc=live_battery_soc,
            )
            errors[key] = msg
            outcomes[key] = _soc_result(key, value, success=False, message=msg)
            write_failed = True

    if verify:
        await _refresh_soc_entities(hass, entity_map)
        for key in SOC_DISPLAY_ORDER:
            want = target[key]
            if key in outcomes and outcomes[key].success:
                continue
            if key in outcomes and not outcomes[key].success:
                continue
            got = _read_soc_key(hass, entity_map, key)
            if got == want:
                outcomes[key] = _soc_result(
                    key,
                    want,
                    success=True,
                    message="Already set",
                    skipped=True,
                )
            elif key in errors:
                outcomes[key] = _soc_result(key, want, success=False, message=errors[key])
            else:
                outcomes[key] = _soc_result(
                    key,
                    want,
                    success=False,
                    message=f"Inverter reports {got}% (expected {want}%)"
                    if got is not None
                    else "No read-back from inverter",
                )
    else:
        await _refresh_soc_entities(hass, entity_map)
        for key in SOC_DISPLAY_ORDER:
            if key in outcomes:
                continue
            want = target[key]
            got = _read_soc_key(hass, entity_map, key)
            if got == want:
                outcomes[key] = _soc_result(
                    key,
                    want,
                    success=True,
                    message="Already set",
                    skipped=True,
                )
            else:
                outcomes[key] = _soc_result(
                    key,
                    want,
                    success=False,
                    message="Not written (a previous step failed)"
                    if write_failed
                    else f"Inverter reports {got}% (expected {want}%)"
                    if got is not None
                    else "No read-back from inverter",
                )

    results = _build_soc_results(target, outcomes)
    if emulate_max_soc:
        from .virtual_max_soc import virtual_max_soc_message

        for row in results:
            if row.get("key") == "max_soc":
                row["success"] = True
                row["skipped"] = True
                row["message"] = virtual_max_soc_message(target["max_soc"])
                break
        else:
            results.append(
                _soc_result(
                    "max_soc",
                    target["max_soc"],
                    success=True,
                    message=virtual_max_soc_message(target["max_soc"]),
                    skipped=True,
                ).to_dict()
            )
    _LOGGER.debug(
        "Applied SOC limits %s (%d writes, %d ok)",
        target,
        len(sequence),
        sum(1 for row in results if row["success"]),
    )
    return results
