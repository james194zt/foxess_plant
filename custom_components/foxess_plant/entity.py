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


def inverter_via_device_id(inverter_device) -> str | None:
    """Return the inverter device's id, to link the plant device under it via `via_device_id`.

    (HA deprecated passing `via_device` identifier tuples; `via_device_id` takes the device id.)
    """
    if inverter_device is None:
        return None
    return inverter_device.id
