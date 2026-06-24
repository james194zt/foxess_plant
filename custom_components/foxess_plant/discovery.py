"""Discover foxess_modbus entities linked to an inverter device."""

from __future__ import annotations

import logging
import re

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
# foxess_modbus device identifiers store INVERTER_MODEL (full PCS string), not INVERTER_BASE.
_EVO_FULL_MODEL = re.compile(r"^EVO \d+-[\d\.]+-H$", re.IGNORECASE)
_H3_PRO_FULL_MODEL = re.compile(r"^[HP]3-Pro-[\d\.]+", re.IGNORECASE)
_H3_SMART_FULL_MODEL = re.compile(r"^H3-[\d\.]+-(?:Smart|M)\b", re.IGNORECASE)


def _model_uses_h3_pro_soc_block(model: str) -> bool:
    """Match inverter base enum or full model string from foxess_modbus device identifiers."""
    text = str(model).strip()
    upper = text.upper()
    if upper in _H3_PRO_SOC_MODELS:
        return True
    if _EVO_FULL_MODEL.match(text):
        return True
    if _H3_PRO_FULL_MODEL.match(text):
        return True
    if _H3_SMART_FULL_MODEL.match(text):
        return True
    if upper.startswith("EVO "):
        return True
    return False


def _device_entry_uses_h3_pro_soc_block(device: dr.DeviceEntry) -> bool:
    if not is_foxess_modbus_device(device):
        return False
    for identifier in device.identifiers:
        if identifier[0] == MODBUS_DOMAIN and len(identifier) >= 2:
            if _model_uses_h3_pro_soc_block(str(identifier[1])):
                return True
    if device.model:
        model_part = str(device.model).split(" - ", 1)[0]
        if _model_uses_h3_pro_soc_block(model_part):
            return True
    return False


def device_uses_h3_pro_soc_block(hass: HomeAssistant, device_id: str) -> bool:
    """True when the linked foxess_modbus inverter uses the 46609–46611 SOC block."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return False
    return _device_entry_uses_h3_pro_soc_block(device)


def resolve_uses_h3_pro_soc_block(
    hass: HomeAssistant,
    device_id: str | None,
    entity_map: dict[str, str] | None = None,
) -> bool:
    """Resolve H3 Pro / EVO SOC block from plant device_id and/or linked number entities."""
    if device_id and device_uses_h3_pro_soc_block(hass, device_id):
        return True
    if not entity_map:
        return False
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    seen: set[str] = set()
    if device_id:
        seen.add(device_id)
    for key in ("min_soc", "max_soc", "min_soc_on_grid"):
        entity_id = entity_map.get(key)
        if not entity_id:
            continue
        entry = entity_reg.async_get(entity_id)
        if entry is None or not entry.device_id or entry.device_id in seen:
            continue
        seen.add(entry.device_id)
        device = device_reg.async_get(entry.device_id)
        if device is not None and _device_entry_uses_h3_pro_soc_block(device):
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


def _entity_id_matches_panel_suffix(entity_id: str, suffix: str) -> bool:
    """Match standard suffixes and long ids such as ``..._pv_power_evo_10``."""
    if not entity_id or not suffix:
        return False
    if entity_id.endswith(f"_{suffix}"):
        return True
    local = entity_id.rsplit(".", 1)[-1]
    if local == suffix:
        return True
    needle = f"_{suffix}_"
    return needle in entity_id


def _entity_id_matches_suffix(entity_id: str, suffix: str) -> bool:
    return _entity_id_matches_panel_suffix(entity_id, suffix)


def _foxess_modbus_host(device: dr.DeviceEntry) -> str | None:
    for identifier in device.identifiers:
        if identifier[0] == MODBUS_DOMAIN and len(identifier) >= 3:
            host = identifier[2]
            if host:
                return str(host)
    return None


def discover_entity_map_extended(hass: HomeAssistant, device_id: str) -> dict[str, str]:
    """Discover entities on the plant device and sibling foxess_modbus devices (same host)."""
    entity_map = discover_entity_map(hass, device_id)
    device_reg = dr.async_get(hass)
    device = device_reg.async_get(device_id)
    if device is None:
        return entity_map

    host = _foxess_modbus_host(device)
    if not host:
        return entity_map

    for entry in device_reg.devices.values():
        if entry.id == device_id or not is_foxess_modbus_device(entry):
            continue
        if _foxess_modbus_host(entry) != host:
            continue
        sibling_map = discover_entity_map(hass, entry.id)
        for key, entity_id in sibling_map.items():
            existing = entity_map.get(key)
            if existing is None or not _state_is_usable(hass, existing):
                entity_map[key] = entity_id
    return entity_map


def _suffixes_for_key(key: str) -> tuple[str, ...]:
    if key in PANEL_ENTITY_SUFFIXES:
        return PANEL_ENTITY_SUFFIXES[key]
    if key in IDENTITY_ENTITY_SUFFIXES:
        return IDENTITY_ENTITY_SUFFIXES[key]
    single = DISCOVERY_SUFFIXES.get(key)
    if isinstance(single, str):
        return (single,)
    if isinstance(single, tuple):
        return single
    return ()


def _integration_domain(hass: HomeAssistant, entity_id: str) -> str | None:
    entry = er.async_get(hass).async_get(entity_id)
    if not entry or not entry.config_entry_id:
        return None
    cfg = hass.config_entries.async_get_entry(entry.config_entry_id)
    return cfg.domain if cfg else None


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
    suffixes = _suffixes_for_key(key)
    if not suffixes:
        return entity_map.get(key)

    candidates: list[str] = []
    mapped = entity_map.get(key)
    if mapped:
        candidates.append(mapped)

    if device_id:
        entity_reg = er.async_get(hass)
        for entry in er.async_entries_for_device(entity_reg, device_id):
            if entry.entity_id:
                candidates.append(entry.entity_id)

    candidates.extend(hass.states.async_entity_ids())

    seen: set[str] = set()
    matches: list[str] = []
    for entity_id in candidates:
        if not entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        if not any(_entity_id_matches_panel_suffix(entity_id, suffix) for suffix in suffixes):
            continue
        if not _state_is_usable(hass, entity_id):
            continue
        matches.append(entity_id)

    if not matches:
        return mapped

    def rank(entity_id: str) -> tuple[int, int, str]:
        on_device = 0
        if device_id:
            entity_reg = er.async_get(hass)
            entry = entity_reg.async_get(entity_id)
            on_device = 0 if entry and entry.device_id == device_id else 1
        modbus = 0 if _integration_domain(hass, entity_id) == MODBUS_DOMAIN else 1
        return (on_device, modbus, entity_id)

    matches.sort(key=rank)
    return matches[0]
