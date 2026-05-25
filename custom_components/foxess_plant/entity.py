"""Shared entity helpers for foxess_plant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def plant_device_info(entry: ConfigEntry) -> DeviceInfo:
    """DeviceInfo linking entities to the plant config entry device."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="FoxESS Plant",
        model="Plant Controller",
    )


def inverter_via_device(inverter_device) -> tuple[str, ...] | None:
    """Return via_device identifier tuple for a foxess_modbus inverter device."""
    if inverter_device is None or not inverter_device.identifiers:
        return None
    return next(iter(inverter_device.identifiers))
