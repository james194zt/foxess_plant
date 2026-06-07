"""FoxESS Plant — central plant control above foxess_modbus."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up global handlers for foxess_plant."""
    from .websocket_api import async_register_ws_handlers

    async_register_ws_handlers(hass)

    async def _register_panel_on_start(_event: Event) -> None:
        if not hass.config_entries.async_entries(DOMAIN):
            return
        from .panel import async_register_panel

        try:
            await async_register_panel(hass)
        except Exception:
            _LOGGER.exception("Fox Plant panel registration failed on HA start")

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_panel_on_start)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import FoxessPlantCoordinator
    from .discovery import discover_entity_map
    from .entity import inverter_via_device
    from .panel import async_register_panel
    from .services import register_services

    data = dict(entry.data)
    fresh_map = discover_entity_map(hass, data["device_id"])
    merged_map = {**data.get("entity_map", {}), **fresh_map}
    if merged_map != data.get("entity_map"):
        data["entity_map"] = merged_map
        hass.config_entries.async_update_entry(entry, data=data)

    device_reg = dr.async_get(hass)
    inverter_device = device_reg.async_get(entry.data["device_id"])
    via = inverter_via_device(inverter_device)
    try:
        device_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="FoxESS Plant",
            model="Plant Controller",
            via_device=via,
        )
    except Exception:
        _LOGGER.exception("Could not link plant device to inverter; continuing without via_device")
        device_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="FoxESS Plant",
            model="Plant Controller",
        )

    coordinator = FoxessPlantCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_update_tariff_sensors(record_history=False)
    register_services(hass)

    try:
        await async_register_panel(hass)
    except Exception:
        _LOGGER.exception("Fox Plant panel registration failed")

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    from .models import PlantConfig
    from .panel import async_update_panel

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    coordinator.update_plant_config(PlantConfig.from_entry_data(entry.data))
    coordinator._setup_tariff_schedule_timer()
    coordinator._setup_octopus_timer()
    coordinator._setup_smart_charge_timer()
    if coordinator._octopus_native_active():
        await coordinator._async_refresh_octopus()
    await coordinator.async_update_tariff_sensors(record_history=False)
    await coordinator.async_request_refresh()
    try:
        await async_update_panel(hass)
    except Exception:
        _LOGGER.exception("Fox Plant panel update failed")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .panel import async_update_panel

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
        try:
            await async_update_panel(hass)
        except Exception:
            pass
    return unload_ok
