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


# H3 Pro / Smart / EVO expose min/max/on-grid SOC at contiguous holding 46609–46611.
_H3_PRO_SOC_MODELS = frozenset({"EVO", "H3_PRO", "H3_SMART"})


def device_uses_h3_pro_soc_block(hass: HomeAssistant, device_id: str) -> bool:
    """True when the linked foxess_modbus inverter uses the 46609–46611 SOC block."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return False
    for identifier in device.identifiers:
        if identifier[0] == MODBUS_DOMAIN and len(identifier) >= 2:
            model = str(identifier[1]).upper()
            if model in _H3_PRO_SOC_MODELS:
                return True
    return False


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


def discover_entity_map(hass: HomeAssistant, device_id: str) -> dict[str, str]:
    """Map logical plant keys to entity IDs on the given foxess_modbus device."""
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    device = device_reg.async_get(device_id)
    if device is None:
        _LOGGER.warning("Device %s not found for entity discovery", device_id)
        return {}

    entity_map: dict[str, str] = {}
    entries = er.async_entries_for_device(entity_reg, device_id)

    for entry in entries:
        if not entry.entity_id:
            continue
        for key, suffix in DISCOVERY_SUFFIXES.items():
            if _match_suffix(entry, suffix) and _should_assign_entity(key, entry.entity_id, entity_map):
                entity_map[key] = entry.entity_id

        for key, suffixes in PANEL_ENTITY_SUFFIXES.items():
            if key in entity_map:
                continue
            for suffix in suffixes:
                if _match_panel_suffix(entry, suffix):
                    entity_map[key] = entry.entity_id
                    break

        for key, suffixes in IDENTITY_ENTITY_SUFFIXES.items():
            if key in entity_map:
                continue
            for suffix in suffixes:
                if _match_suffix(entry, suffix):
                    entity_map[key] = entry.entity_id
                    break

    _LOGGER.debug("Discovered entity map for %s: %s", device_id, entity_map)
    return entity_map


def missing_charge_period_entities(entity_map: dict[str, str]) -> list[str]:
    """Return charge-period keys missing from the map."""
    return [key for key in CHARGE_PERIOD_KEYS if key not in entity_map]


def _entity_id_matches_suffix(entity_id: str, suffix: str) -> bool:
    if not entity_id or not suffix:
        return False
    if entity_id.endswith(f"_{suffix}"):
        return True
    local = entity_id.rsplit(".", 1)[-1]
    if local == suffix:
        return True
    return f"_{suffix}_" in entity_id


def _suffixes_for_key(key: str) -> tuple[str, ...]:
    if key in PANEL_ENTITY_SUFFIXES:
        return PANEL_ENTITY_SUFFIXES[key]
    if key in IDENTITY_ENTITY_SUFFIXES:
        return IDENTITY_ENTITY_SUFFIXES[key]
    single = DISCOVERY_SUFFIXES.get(key)
    return (single,) if single else ()


def _state_is_usable(hass: HomeAssistant, entity_id: str | None) -> bool:
    if not entity_id:
        return False
    state = hass.states.get(entity_id)
    if state is None:
        return False
    return state.state not in ("unavailable", "unknown", None, "")


def resolve_entity_id(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    key: str,
    *,
    device_id: str | None = None,
) -> str | None:
    """Resolve a plant logical key to a live entity_id (stored map + runtime suffix fallbacks)."""
    mapped = entity_map.get(key)
    if _state_is_usable(hass, mapped):
        return mapped

    suffixes = _suffixes_for_key(key)
    if not suffixes:
        return mapped

    candidates: list[str] = []
    if device_id:
        entity_reg = er.async_get(hass)
        for entry in er.async_entries_for_device(entity_reg, device_id):
            if entry.entity_id:
                candidates.append(entry.entity_id)
    if not candidates:
        candidates = list(hass.states.async_entity_ids())

    for suffix in suffixes:
        for entity_id in candidates:
            if _entity_id_matches_suffix(entity_id, suffix) and _state_is_usable(hass, entity_id):
                return entity_id
    return mapped
