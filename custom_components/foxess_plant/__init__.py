"""FoxESS Plant — central plant control above foxess_modbus."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PLATFORMS
from .coordinator import FoxessPlantCoordinator
from .panel import async_register_panel, async_update_panel
from .services import register_services
from .websocket_api import async_register_ws_handlers

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up global handlers for foxess_plant."""
    async_register_ws_handlers(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .discovery import discover_entity_map

    data = dict(entry.data)
    fresh_map = discover_entity_map(hass, data["device_id"])
    merged_map = {**data.get("entity_map", {}), **fresh_map}
    if merged_map != data.get("entity_map"):
        data["entity_map"] = merged_map
        hass.config_entries.async_update_entry(entry, data=data)

    coordinator = FoxessPlantCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    register_services(hass)
    await async_register_panel(hass)

    device_reg = dr.async_get(hass)
    inverter_device = device_reg.async_get(entry.data["device_id"])
    via = next(iter(inverter_device.identifiers)) if inverter_device else None
    device_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="FoxESS Plant",
        model="Plant Controller",
        via_device=via,
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator: FoxessPlantCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    from .models import PlantConfig

    coordinator.update_plant_config(PlantConfig.from_entry_data(entry.data))
    await coordinator.async_request_refresh()
    await async_update_panel(hass)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: FoxessPlantCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
        await async_update_panel(hass)
    return unload_ok
