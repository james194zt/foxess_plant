"""Sensor platform for foxess_plant."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FoxessPlantCoordinator

ANALYTICS_SENSORS = (
    ("self_consumption_percent_today", PERCENTAGE, "Self-consumption today", "mdi:solar-power"),
    ("self_sufficiency_percent_today", PERCENTAGE, "Self-sufficiency today", "mdi:home-lightning-bolt"),
    ("pv_production_kwh_today", UnitOfEnergy.KILO_WATT_HOUR, "PV production today", "mdi:solar-power-variant"),
    ("load_consumption_kwh_today", UnitOfEnergy.KILO_WATT_HOUR, "Load consumption today", "mdi:home-import-outline"),
    ("load_from_grid_kwh_today", UnitOfEnergy.KILO_WATT_HOUR, "Load from grid today", "mdi:transmission-tower"),
    ("pv_to_grid_kwh_today", UnitOfEnergy.KILO_WATT_HOUR, "PV export today", "mdi:transmission-tower-export"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FoxessPlantCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = [FoxessPlantModeSensor(coordinator, entry)]
    for key, unit, name, icon in ANALYTICS_SENSORS:
        entities.append(FoxessPlantAnalyticsSensor(coordinator, entry, key, unit, name, icon))
    async_add_entities(entities)


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
            "active_storm_triggers": state.get("active_storm_triggers"),
            "active_outage_triggers": state.get("active_outage_triggers"),
            "forecast_armed": state.get("forecast_armed"),
            "tariff_modes": state.get("tariff_modes"),
        }


class FoxessPlantAnalyticsSensor(CoordinatorEntity[FoxessPlantCoordinator], SensorEntity):
    """Daily energy analytics derived from mapped inverter entities."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: FoxessPlantCoordinator,
        entry: ConfigEntry,
        key: str,
        unit: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = f"{entry.title} {name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        if unit == PERCENTAGE:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = None
        else:
            self._attr_device_class = SensorDeviceClass.ENERGY

    @property
    def available(self) -> bool:
        analytics = (self.coordinator.data or {}).get("analytics") or {}
        return self._key in analytics

    @property
    def native_value(self) -> float | None:
        analytics = (self.coordinator.data or {}).get("analytics") or {}
        value = analytics.get(self._key)
        return float(value) if value is not None else None
