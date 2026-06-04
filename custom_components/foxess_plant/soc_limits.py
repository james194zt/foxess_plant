"""Apply FoxESS SOC limits via foxess_modbus number entities."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

SOC_KEYS = ("min_soc", "min_soc_on_grid", "max_soc")

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


def force_soc_write_sequence(target: dict[str, int]) -> list[tuple[str, int]]:
    """Always write all three SOC registers in inverter-safe order (explicit save)."""
    t = clamp_soc_values(target["min_soc"], target["min_soc_on_grid"], target["max_soc"])
    return [(key, t[key]) for key in ("max_soc", "min_soc_on_grid", "min_soc")]


async def _refresh_soc_entities(hass: HomeAssistant, entity_map: dict[str, str]) -> None:
    for key in SOC_KEYS:
        entity_id = entity_map.get(key)
        if entity_id:
            await hass.services.async_call(
                "homeassistant",
                "update_entity",
                {"entity_id": entity_id},
                blocking=True,
            )


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


def _raise_soc_error(err: BaseException) -> None:
    message = str(err)
    if "IllegalValue" in message or "46609" in message or "46610" in message or "46611" in message:
        raise HomeAssistantError(f"{_ILLEGAL_VALUE_HINT} Details: {message}") from err
    raise HomeAssistantError(message) from err


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
) -> None:
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

    if force_write:
        sequence = force_soc_write_sequence(target)
    else:
        sequence = compute_soc_write_sequence(target, live_current)

    for key, value in sequence:
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
        except Exception as err:
            _raise_soc_error(err)

    if verify:
        await verify_soc_limits(hass, entity_map, target)

    _LOGGER.debug("Applied SOC limits %s (%d writes)", target, len(sequence))
