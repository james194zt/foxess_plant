"""Sensor platform for foxess_plant."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FoxessPlantCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FoxessPlantCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([FoxessPlantModeSensor(coordinator, entry)])


class FoxessPlantModeSensor(CoordinatorEntity[FoxessPlantCoordinator], SensorEntity):
    """Current plant control mode."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:solar-power"

    def __init__(self, coordinator: FoxessPlantCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_plant_mode"
        self._attr_name = f"{entry.title} mode"

    @property
    def native_value(self) -> str:
        return self.coordinator.plant.plant_mode()

    @property
    def extra_state_attributes(self) -> dict:
        state = self.coordinator.data or {}
        return {
            "control_active": state.get("control_active"),
            "override_active": state.get("override_active"),
            "override_reason": state.get("override_reason"),
            "drift": state.get("drift"),
            "inverter": state.get("inverter"),
            "plant_id": self._entry.entry_id,
        }
