"""Discover foxess_modbus entities linked to an inverter device."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CHARGE_PERIOD_KEYS,
    DISCOVERY_SUFFIXES,
    IDENTITY_ENTITY_SUFFIXES,
    MODBUS_DOMAIN,
    PANEL_ENTITY_SUFFIXES,
)

_LOGGER = logging.getLogger(__name__)


def is_foxess_modbus_device(device: dr.DeviceEntry) -> bool:
    """Return True if the device belongs to foxess_modbus."""
    return any(identifier[0] == MODBUS_DOMAIN for identifier in device.identifiers)


def inverter_target_from_device(device: dr.DeviceEntry) -> str:
    """Resolve the inverter target string accepted by foxess_modbus services."""
    for identifier in device.identifiers:
        if identifier[0] == MODBUS_DOMAIN and len(identifier) >= 4:
            friendly_name = identifier[3]
            if friendly_name:
                return str(friendly_name)
    return device.id


def _match_suffix(entry: er.RegistryEntry, suffix: str) -> bool:
    return entry.entity_id.endswith(f"_{suffix}") or entry.unique_id.endswith(f"_{suffix}")


def _match_panel_suffix(entry: er.RegistryEntry, suffix: str) -> bool:
    """Match standard suffixes and long EVO ids such as ``..._pv_power_evo_10``."""
    if _match_suffix(entry, suffix):
        return True
    needle = f"_{suffix}_"
    uid = entry.unique_id or ""
    return needle in entry.entity_id or needle in uid


def _should_assign_entity(key: str, entity_id: str, entity_map: dict[str, str]) -> bool:
    """Prefer writable number entities over read-only sensors for SOC controls."""
    existing = entity_map.get(key)
    if existing is None:
        return True
    if entity_id.startswith("number."):
        return True
    return not existing.startswith("number.")


def _foxess_modbus_friendly_name(device: dr.DeviceEntry | None) -> str | None:
    if device is None:
        return None
    for identifier in device.identifiers:
        if identifier[0] == MODBUS_DOMAIN and len(identifier) >= 4:
            friendly_name = identifier[3]
            if friendly_name:
                return str(friendly_name)
    return None


def _entry_belongs_to_inverter(
    entry: er.RegistryEntry,
    *,
    device_ids: set[str],
    friendly_name: str | None,
) -> bool:
    if entry.device_id and entry.device_id in device_ids:
        return True
    if not friendly_name:
        return False
    uid = entry.unique_id or ""
    if not uid.startswith("foxess_modbus_"):
        return False
    return uid.startswith(f"foxess_modbus_{friendly_name}_")


def _match_modbus_key(entry: er.RegistryEntry, key: str, suffix: str) -> bool:
    if _match_suffix(entry, suffix):
        return True
    if _match_panel_suffix(entry, suffix):
        return True
    uid = entry.unique_id or ""
    if uid.startswith("foxess_modbus_") and uid.endswith(f"_{key}"):
        return True
    return False


def _is_foxess_modbus_entry(entry: er.RegistryEntry) -> bool:
    platform = getattr(entry, "platform", None)
    if platform == MODBUS_DOMAIN:
        return True
    uid = entry.unique_id or ""
    return uid.startswith("foxess_modbus_")


def _device_linked_entries(
    entity_reg: er.EntityRegistry,
    device_id: str,
) -> list[er.RegistryEntry]:
    try:
        return list(
            entity_reg.async_entries_for_device(
                device_id,
                include_disabled_entities=True,
            )
        )
    except TypeError:
        return list(entity_reg.async_entries_for_device(device_id))


def _registry_entries_for_inverter(
    hass: HomeAssistant,
    device_id: str,
) -> list[er.RegistryEntry]:
    """Collect foxess_modbus registry entries for an inverter device.

    After modbus reload/migration, Yield Total and other sensors may remain in the
    entity registry but no longer be linked to the device_id FoxESS Plant stores.
    """
    try:
        device_reg = dr.async_get(hass)
        entity_reg = er.async_get(hass)

        device = device_reg.async_get(device_id)
        if device is None:
            return []

        friendly_name = _foxess_modbus_friendly_name(device)
        device_ids: set[str] = {device_id}
        if friendly_name:
            for candidate in device_reg.devices.values():
                if not is_foxess_modbus_device(candidate):
                    continue
                if _foxess_modbus_friendly_name(candidate) == friendly_name:
                    device_ids.add(candidate.id)

        by_entity_id: dict[str, er.RegistryEntry] = {}
        for linked_device_id in device_ids:
            for entry in _device_linked_entries(entity_reg, linked_device_id):
                if entry.entity_id:
                    by_entity_id[entry.entity_id] = entry

        if friendly_name:
            for entry in entity_reg.entities.values():
                if entry.entity_id in by_entity_id:
                    continue
                if not _is_foxess_modbus_entry(entry):
                    continue
                if _entry_belongs_to_inverter(
                    entry,
                    device_ids=device_ids,
                    friendly_name=friendly_name,
                ):
                    by_entity_id[entry.entity_id] = entry

        return list(by_entity_id.values())
    except Exception:
        _LOGGER.exception("Expanded foxess_modbus registry scan failed for %s", device_id)
        try:
            entity_reg = er.async_get(hass)
            return _device_linked_entries(entity_reg, device_id)
        except Exception:
            _LOGGER.exception("Fallback entity registry scan failed for %s", device_id)
            return []


def merge_entity_maps(
    hass: HomeAssistant,
    existing: dict[str, str],
    fresh: dict[str, str],
) -> dict[str, str]:
    """Merge discovery results, preferring fresh ids.

    Never drop an existing mapping just because the entity state is temporarily
    unavailable — that wiped maps after modbus reload and broke Plant sensors.
    """
    merged = {**existing, **fresh}
    entity_reg = er.async_get(hass)
    for key, entity_id in list(merged.items()):
        if not entity_id or entity_reg.async_get(entity_id) is None:
            del merged[key]
    return merged


def discover_entity_map(hass: HomeAssistant, device_id: str) -> dict[str, str]:
    """Map logical plant keys to entity IDs on the given foxess_modbus device."""
    device_reg = dr.async_get(hass)

    device = device_reg.async_get(device_id)
    if device is None:
        _LOGGER.warning("Device %s not found for entity discovery", device_id)
        return {}

    try:
        entries = _registry_entries_for_inverter(hass, device_id)
        entity_map: dict[str, str] = {}

        for entry in entries:
            if not entry.entity_id:
                continue
            for key, suffix in DISCOVERY_SUFFIXES.items():
                if _match_modbus_key(entry, key, suffix) and _should_assign_entity(
                    key, entry.entity_id, entity_map
                ):
                    entity_map[key] = entry.entity_id

            for key, suffixes in PANEL_ENTITY_SUFFIXES.items():
                if key in entity_map:
                    continue
                for suffix in suffixes:
                    if _match_modbus_key(entry, key, suffix):
                        entity_map[key] = entry.entity_id
                        break

            for key, suffixes in IDENTITY_ENTITY_SUFFIXES.items():
                if key in entity_map:
                    continue
                for suffix in suffixes:
                    if _match_modbus_key(entry, key, suffix):
                        entity_map[key] = entry.entity_id
                        break

        if "total_yield_total" not in entity_map:
            _LOGGER.warning(
                "total_yield_total not discovered for device %s (%s); "
                "scanned %d foxess_modbus registry entries",
                device_id,
                device.name,
                len(entries),
            )
        _LOGGER.debug("Discovered entity map for %s: %s", device_id, entity_map)
        return entity_map
    except Exception:
        _LOGGER.exception("Entity discovery failed for device %s", device_id)
        return {}


def missing_charge_period_entities(entity_map: dict[str, str]) -> list[str]:
    """Return charge-period keys missing from the map."""
    return [key for key in CHARGE_PERIOD_KEYS if key not in entity_map]
