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

from .const import MODBUS_DOMAIN
from .discovery import device_uses_h3_pro_soc_block

_LOGGER = logging.getLogger(__name__)

SOC_KEYS = ("min_soc", "min_soc_on_grid", "max_soc")
SOC_DISPLAY_ORDER = ("min_soc", "min_soc_on_grid", "max_soc")
SOC_LABELS = {
    "min_soc": "Off-grid Min. SOC",
    "min_soc_on_grid": "System Min. SOC",
    "max_soc": "System Max. SOC",
}

# Physical holding register layout (not logical sort order): 46609=min, 46610=max, 46611=on-grid.
H3_PRO_SOC_BLOCK_START = 46609
H3_PRO_SOC_BLOCK_KEYS = ("min_soc", "max_soc", "min_soc_on_grid")


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
    "Modbus IllegalValue on an SOC register (EVO/H3 Pro: 46609 min, 46610 max, 46611 on-grid). "
    "The inverter requires off-grid min ≤ system min ≤ max. "
    "Try the same values on the FoxESS Modbus **number** entities in Developer Tools. "
    "If those fail too, confirm the inverter model in FoxESS Modbus is EVO and that the "
    "Fox app is not locking settings."
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
) -> str:
    message = str(err)
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


async def _atomic_h3_pro_soc_write(
    hass: HomeAssistant,
    inverter_target: str,
    target: dict[str, int],
) -> None:
    """One FC16 write for 46609–46611 (min, max, on-grid) — matches Fox app behaviour."""
    values = [target[key] for key in H3_PRO_SOC_BLOCK_KEYS]
    await hass.services.async_call(
        MODBUS_DOMAIN,
        "write_registers",
        {
            "inverter": inverter_target,
            "start_address": H3_PRO_SOC_BLOCK_START,
            "values": ",".join(str(v) for v in values),
        },
        blocking=True,
    )


async def _apply_atomic_soc_block(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    target: dict[str, int],
    *,
    inverter_target: str,
    live_battery_soc: float | None,
) -> list[dict[str, Any]] | None:
    """Try a single contiguous SOC block write; return results or None to fall back."""
    try:
        await _atomic_h3_pro_soc_write(hass, inverter_target, target)
    except Exception as err:
        _LOGGER.info(
            "Atomic SOC block write failed (%s); falling back to per-register writes",
            err,
        )
        return None

    outcomes: dict[str, SocWriteResult] = {}
    for key in SOC_DISPLAY_ORDER:
        outcomes[key] = await _verify_soc_key(hass, entity_map, key, target[key])
        if not outcomes[key].success and key == "max_soc":
            battery_hint = _max_soc_battery_hint(live_battery_soc, target["max_soc"])
            if battery_hint:
                outcomes[key] = _soc_result(
                    key,
                    target[key],
                    success=False,
                    message=battery_hint,
                )

    results = _build_soc_results(target, outcomes)
    if all(row["success"] for row in results):
        return results

    _LOGGER.info("Atomic SOC block read-back incomplete; falling back to per-register writes")
    return None


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
) -> list[dict[str, Any]]:
    """Write min / on-grid / max SOC through foxess_modbus number entities."""
    target = validate_soc_limits_for_write(min_soc, min_soc_on_grid, max_soc)

    if force_write or current is None:
        await _refresh_soc_entities(hass, entity_map)
        live_current = read_soc_current(hass, entity_map)
    else:
        live_current = {
            key: parsed
            for key in SOC_KEYS
            if (parsed := _coerce_soc(current.get(key))) is not None
        }

    sequence = compute_soc_write_sequence(target, live_current)
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

    if (
        verify
        and inverter_target
        and device_id
        and device_uses_h3_pro_soc_block(hass, device_id)
        and sequence
    ):
        atomic_results = await _apply_atomic_soc_block(
            hass,
            entity_map,
            target,
            inverter_target=inverter_target,
            live_battery_soc=live_battery_soc,
        )
        if atomic_results is not None:
            return atomic_results
        await _refresh_soc_entities(hass, entity_map)
        live_current = read_soc_current(hass, entity_map)
        sequence = compute_soc_write_sequence(target, live_current)

    # Ordered transitions (e.g. lower mid before max) — never blind max-first writes.
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
            await hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": entity_id, "value": value},
                blocking=True,
            )
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
    _LOGGER.debug(
        "Applied SOC limits %s (%d writes, %d ok)",
        target,
        len(sequence),
        sum(1 for row in results if row["success"]),
    )
    return results
