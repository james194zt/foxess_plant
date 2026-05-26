"""Apply FoxESS SOC limits via foxess_modbus number entities."""

from __future__ import annotations

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
) -> None:
    """Write min / on-grid / max SOC through foxess_modbus number entities."""
    target = clamp_soc_values(min_soc, min_soc_on_grid, max_soc)
    sequence = compute_soc_write_sequence(target, current or {})

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
    _LOGGER.debug("Applied SOC limits %s (%d writes)", target, len(sequence))
