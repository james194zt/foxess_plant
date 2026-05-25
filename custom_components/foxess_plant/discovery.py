"""Discover foxess_modbus entities linked to an inverter device."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CHARGE_PERIOD_KEYS, DISCOVERY_SUFFIXES

_LOGGER = logging.getLogger(__name__)


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
            if key in entity_map:
                continue
            if entry.entity_id.endswith(f"_{suffix}") or entry.unique_id.endswith(f"_{suffix}"):
                entity_map[key] = entry.entity_id

    _LOGGER.debug("Discovered entity map for %s: %s", device_id, entity_map)
    return entity_map


def missing_charge_period_entities(entity_map: dict[str, str]) -> list[str]:
    """Return charge-period keys missing from the map."""
    return [key for key in CHARGE_PERIOD_KEYS if key not in entity_map]
