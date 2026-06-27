"""TEMPORARY Modbus lab — EVO scheduler / SOC testing (foxess_modbus PR #1134 paths).

Search MODBUS_LAB in the repo to remove this module and its UI wiring.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .charge_period import apply_charge_periods
from .const import CHARGE_PERIOD_KEYS, MODBUS_DOMAIN
from .entity_live import async_read_entity_key_live, async_read_soc_live
from .models import ChargePeriodConfig
from .remote_control import set_remote_control_mode
from .soc_limits import apply_soc_limits, read_soc_current

_LOGGER = logging.getLogger(__name__)

# EVO charge-period holding registers (PR nathanmarlor/foxess_modbus#1134).
EVO_CHARGE_PERIOD_SPECS: tuple[dict[str, int], ...] = (
    {"enable": 48010, "start": 48011, "end": 48012, "mode": 48013},
    {"enable": 48020, "start": 48021, "end": 48022, "mode": 48023},
)
EVO_MODE_CHARGE = 6
EVO_MODE_NO_CHARGE = 1

_RAW_REGISTER_BLOCKS: tuple[tuple[str, int, int], ...] = (
    ("evo_period_1", 48010, 4),
    ("evo_period_2", 48020, 4),
    ("soc_limits", 46609, 3),
    ("work_mode", 49203, 1),
)


def _serialize_time(hhmm: str, *, enabled: bool) -> int:
    if not enabled:
        return 0
    parts = str(hhmm or "00:00").strip().split(":")
    hour = int(parts[0]) if parts else 0
    minute = int(parts[1]) if len(parts) > 1 else 0
    return (hour << 8) | minute


async def _read_holding(
    hass: HomeAssistant,
    inverter_ref: str,
    start_address: int,
    count: int,
) -> tuple[dict[int, int] | None, str | None]:
    try:
        response = await hass.services.async_call(
            MODBUS_DOMAIN,
            "read_registers",
            {
                "inverter": inverter_ref,
                "start_address": start_address,
                "count": count,
                "type": "holding",
            },
            blocking=True,
            return_response=True,
        )
    except Exception as err:
        return None, str(err)
    if not isinstance(response, dict):
        return None, "No response from read_registers"
    if response.get("error"):
        return None, str(response["error"])
    values = response.get("values") or {}
    return {int(k): int(v) for k, v in values.items()}, None


async def _write_holding_block(
    hass: HomeAssistant,
    inverter_ref: str,
    start_address: int,
    values: list[int],
) -> None:
    payload = ",".join(str(v) for v in values)
    await hass.services.async_call(
        MODBUS_DOMAIN,
        "write_registers",
        {
            "inverter": inverter_ref,
            "start_address": start_address,
            "values": payload,
        },
        blocking=True,
    )


async def apply_evo_charge_periods_direct(
    hass: HomeAssistant,
    inverter_ref: str,
    periods: list[ChargePeriodConfig],
) -> list[dict[str, Any]]:
    """PR #1134 path: one FC16 block per period including mode register 48013/48023."""
    results: list[dict[str, Any]] = []
    for idx, period in enumerate(periods[: len(EVO_CHARGE_PERIOD_SPECS)]):
        spec = EVO_CHARGE_PERIOD_SPECS[idx]
        grid = bool(period.enable_charge_from_grid)
        force = bool(period.enable_force_charge)
        writes: list[tuple[int, int]] = [
            (spec["start"], _serialize_time(period.start, enabled=force)),
            (spec["end"], _serialize_time(period.end, enabled=force)),
            (spec["enable"], 1 if grid else 0),
            (spec["mode"], EVO_MODE_CHARGE if grid else EVO_MODE_NO_CHARGE),
        ]
        start_addr = min(address for address, _ in writes)
        end_addr = max(address for address, _ in writes)
        block = [0] * (end_addr - start_addr + 1)
        for address, value in writes:
            block[address - start_addr] = value
        label = f"evo_direct_period_{idx + 1}"
        try:
            await _write_holding_block(hass, inverter_ref, start_addr, block)
            results.append({"key": label, "success": True, "attempted": period.to_dict()})
        except Exception as err:
            results.append(
                {
                    "key": label,
                    "success": False,
                    "attempted": period.to_dict(),
                    "error": str(err),
                }
            )
            raise HomeAssistantError(
                f"Direct EVO charge period {idx + 1} write failed: {err}"
            ) from err
    return results


async def _refresh_charge_period_entities(hass: HomeAssistant, entity_map: dict[str, str]) -> None:
    tasks = []
    for key in CHARGE_PERIOD_KEYS:
        entity_id = entity_map.get(key)
        if entity_id:
            tasks.append(
                hass.services.async_call(
                    "homeassistant",
                    "update_entity",
                    {"entity_id": entity_id},
                    blocking=True,
                )
            )
    if tasks:
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.35)


def _normalize_period_time(value: str | None) -> str | None:
    if not value or value in ("unknown", "unavailable"):
        return None
    parts = str(value).split(":")
    if len(parts) >= 2:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    return str(value)


def _read_charge_period_entities(hass: HomeAssistant, entity_map: dict[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx in (1, 2):
        prefix = f"time_period_{idx}"
        force = hass.states.get(entity_map.get(f"{prefix}_enable_force_charge", ""))
        grid = hass.states.get(entity_map.get(f"{prefix}_enable_charge_from_grid", ""))
        start = hass.states.get(entity_map.get(f"{prefix}_start", ""))
        end = hass.states.get(entity_map.get(f"{prefix}_end", ""))
        out.append(
            {
                "enable_force_charge": (force.state if force else None) in ("on", "true", "1"),
                "enable_charge_from_grid": (grid.state if grid else None) in ("on", "true", "1"),
                "start": _normalize_period_time(start.state if start else None),
                "end": _normalize_period_time(end.state if end else None),
            }
        )
    return out


async def read_modbus_lab_state(coordinator: Any) -> dict[str, Any]:
    """Live entity snapshot + raw holding registers for the lab page."""
    hass = coordinator.hass
    plant = coordinator.plant
    entity_map = plant.entity_map
    inverter_ref = plant.inverter_target or plant.device_id

    await _refresh_charge_period_entities(hass, entity_map)
    soc = await async_read_soc_live(hass, entity_map)
    entities = {
        "work_mode": await async_read_entity_key_live(hass, entity_map, "work_mode"),
        "remote_control": await async_read_entity_key_live(hass, entity_map, "remote_control"),
        "min_soc": soc.get("min_soc"),
        "min_soc_on_grid": soc.get("min_soc_on_grid"),
        "max_soc": soc.get("max_soc"),
        "charge_periods": _read_charge_period_entities(hass, entity_map),
    }
    entities["work_mode_options"] = coordinator._entity_options("work_mode")
    entities["remote_control_options"] = coordinator._entity_options("remote_control")

    registers: dict[str, Any] = {}
    register_errors: dict[str, str] = {}
    for block_id, start, count in _RAW_REGISTER_BLOCKS:
        values, err = await _read_holding(hass, inverter_ref, start, count)
        if err:
            register_errors[block_id] = err
        else:
            registers[block_id] = values

    schedule = plant.plant_schedule
    return {
        "entities": entities,
        "registers": registers,
        "register_errors": register_errors,
        "inverter_ref": inverter_ref,
        "control_active": plant.control_active,
        "plant_schedule": schedule.to_dict() if hasattr(schedule, "to_dict") else {},
        "fox_scheduler": coordinator._fox_scheduler_state(),
        "virtual_max_soc": plant.virtual_soc.max_soc,
        "hardware_max_supported": plant.virtual_soc.hardware_max_supported,
    }


async def apply_modbus_lab(coordinator: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Apply lab writes — bypasses SmartCharge/StormSafe but requires plant control."""
    if not coordinator.plant.control_active:
        raise HomeAssistantError("Take plant control before applying Modbus lab writes")

    hass = coordinator.hass
    plant = coordinator.plant
    entity_map = plant.entity_map
    inverter_ref = plant.inverter_target or plant.device_id
    results: list[dict[str, Any]] = []

    if payload.get("work_mode"):
        mode = str(payload["work_mode"])
        try:
            await coordinator._set_work_mode(mode)
            results.append({"key": "work_mode", "success": True, "attempted": mode})
        except Exception as err:
            results.append({"key": "work_mode", "success": False, "error": str(err)})
            raise

    if payload.get("remote_control") is not None:
        rc = str(payload["remote_control"])
        try:
            await set_remote_control_mode(hass, entity_map, rc)
            results.append({"key": "remote_control", "success": True, "attempted": rc})
        except Exception as err:
            results.append({"key": "remote_control", "success": False, "error": str(err)})
            raise

    soc_keys = ("min_soc", "min_soc_on_grid", "max_soc")
    if all(k in payload for k in soc_keys):
        min_soc = int(payload["min_soc"])
        min_soc_on_grid = int(payload["min_soc_on_grid"])
        max_soc = int(payload["max_soc"])
        force_hardware = bool(payload.get("force_hardware_max_soc"))
        from .discovery import device_is_evo
        from .virtual_max_soc import emulate_max_soc

        is_evo = device_is_evo(hass, plant.device_id, entity_map)
        emulate_max = False if force_hardware else (True if is_evo else emulate_max_soc(coordinator))
        try:
            rows = await apply_soc_limits(
                hass,
                entity_map,
                min_soc=min_soc,
                min_soc_on_grid=min_soc_on_grid,
                max_soc=max_soc,
                force_write=True,
                verify=True,
                inverter_target=inverter_ref,
                device_id=plant.device_id,
                live_battery_soc=coordinator._entity_float("battery_soc"),
                emulate_max_soc=emulate_max,
            )
            results.append({"key": "soc_limits", "success": True, "rows": rows})
        except Exception as err:
            results.append({"key": "soc_limits", "success": False, "error": str(err)})
            raise

    raw_periods = payload.get("charge_periods")
    if isinstance(raw_periods, list) and raw_periods:
        periods = [ChargePeriodConfig.from_dict(p) for p in raw_periods[:2]]
        path = str(payload.get("charge_period_path") or "modbus_service")
        try:
            if path == "evo_direct":
                await apply_evo_charge_periods_direct(hass, inverter_ref, periods)
                results.append({"key": "charge_periods", "success": True, "path": path})
            else:
                await apply_charge_periods(
                    hass,
                    inverter_ref,
                    periods,
                    entity_map=entity_map,
                )
                results.append({"key": "charge_periods", "success": True, "path": path})
        except Exception as err:
            results.append(
                {"key": "charge_periods", "success": False, "path": path, "error": str(err)}
            )
            raise

    schedule_payload = payload.get("plant_schedule")
    if isinstance(schedule_payload, dict):
        try:
            await coordinator.async_save_plant_schedule(dict(schedule_payload))
            results.append({"key": "plant_schedule", "success": True})
        except Exception as err:
            results.append({"key": "plant_schedule", "success": False, "error": str(err)})
            raise

    if payload.get("apply_schedule_now"):
        from .schedule_runner import apply_current_schedule_state

        try:
            await apply_current_schedule_state(coordinator, force=True)
            results.append({"key": "apply_schedule_now", "success": True})
        except Exception as err:
            results.append({"key": "apply_schedule_now", "success": False, "error": str(err)})
            raise

    await coordinator.async_request_refresh()
    live = await read_modbus_lab_state(coordinator)
    return {"results": results, "live": live, "soc_current": read_soc_current(hass, entity_map)}
