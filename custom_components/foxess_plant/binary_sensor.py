"""Binary sensor platform for foxess_plant."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    async_add_entities(
        [
            FoxessPlantControlActiveBinary(coordinator, entry),
            FoxessPlantOverrideActiveBinary(coordinator, entry),
            FoxessPlantDriftBinary(coordinator, entry),
        ]
    )


class _PlantBinary(CoordinatorEntity[FoxessPlantCoordinator], BinarySensorEntity):
    def __init__(
        self,
        coordinator: FoxessPlantCoordinator,
        entry: ConfigEntry,
        suffix: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_name = f"{entry.title} {name}"
        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class FoxessPlantControlActiveBinary(_PlantBinary):
    _attr_entity_category = None

    def __init__(self, coordinator: FoxessPlantCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "control_active", "control active", "mdi:shield-check")

    @property
    def is_on(self) -> bool:
        return self.coordinator.plant.control_active


class FoxessPlantOverrideActiveBinary(_PlantBinary):
    def __init__(self, coordinator: FoxessPlantCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "override_active", "period override", "mdi:clock-alert")

    @property
    def is_on(self) -> bool:
        return self.coordinator.plant.override.active


class FoxessPlantDriftBinary(_PlantBinary):
    def __init__(self, coordinator: FoxessPlantCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "control_drift", "control drift", "mdi:alert-circle")

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return bool(data.get("drift"))
