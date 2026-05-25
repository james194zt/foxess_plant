"""Button platform for foxess_plant."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity import plant_device_info
from .const import DOMAIN
from .coordinator import FoxessPlantCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FoxessPlantCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [
            FoxessPlantApplyBaselineButton(coordinator, entry),
            FoxessPlantDisarmOverrideButton(coordinator, entry),
        ]
    )


class FoxessPlantApplyBaselineButton(CoordinatorEntity[FoxessPlantCoordinator], ButtonEntity):
    def __init__(self, coordinator: FoxessPlantCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = plant_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_apply_baseline"
        self._attr_name = f"{entry.title} apply baseline"
        self._attr_icon = "mdi:backup-restore"

    async def async_press(self) -> None:
        await self.coordinator.async_apply_baseline()


class FoxessPlantDisarmOverrideButton(CoordinatorEntity[FoxessPlantCoordinator], ButtonEntity):
    def __init__(self, coordinator: FoxessPlantCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = plant_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_disarm_override"
        self._attr_name = f"{entry.title} disarm override"
        self._attr_icon = "mdi:shield-off"

    async def async_press(self) -> None:
        await self.coordinator.async_disarm_override()
