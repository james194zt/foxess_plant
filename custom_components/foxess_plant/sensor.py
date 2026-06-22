"""Sensor platform for foxess_plant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .entity import plant_device_info
from .const import DOMAIN
from .coordinator import FoxessPlantCoordinator
from .solcast_forecast_metrics import FORECAST_NEXT_X_HOURS
from .tariff_currency import minor_to_major, normalize_tariff_currency
from .tariff_schedule import tariff_sensor_unique_id

ANALYTICS_SENSORS = (
    ("self_consumption_percent_today", PERCENTAGE, "Self-consumption today", "mdi:solar-power"),
    ("self_sufficiency_percent_today", PERCENTAGE, "Self-sufficiency today", "mdi:home-lightning-bolt"),
    ("pv_production_kwh_today", UnitOfEnergy.KILO_WATT_HOUR, "PV production today", "mdi:solar-power-variant"),
    ("load_consumption_kwh_today", UnitOfEnergy.KILO_WATT_HOUR, "Load consumption today", "mdi:home-import-outline"),
    ("load_from_grid_kwh_today", UnitOfEnergy.KILO_WATT_HOUR, "Load from grid today", "mdi:transmission-tower"),
    ("pv_to_grid_kwh_today", UnitOfEnergy.KILO_WATT_HOUR, "PV export today", "mdi:transmission-tower-export"),
)


@dataclass(frozen=True)
class SolcastSensorSpec:
    """Maps to flattened keys on coordinator solcast state (see solcast_forecast_metrics)."""

    metric_key: str
    unique_suffix: str
    name: str
    unit: str
    icon: str
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    is_timestamp: bool = False
    include_forecast_attrs: bool = False


# Friendly names aligned with ha-solcast-solar for dashboard/automation portability.
SOLCAST_FORECAST_SENSORS: tuple[SolcastSensorSpec, ...] = (
    SolcastSensorSpec(
        "forecast_today_kwh",
        "solcast_forecast_today",
        "Forecast today",
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
        include_forecast_attrs=True,
    ),
    SolcastSensorSpec(
        "forecast_tomorrow_kwh",
        "solcast_forecast_tomorrow",
        "Forecast tomorrow",
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
        include_forecast_attrs=True,
    ),
    SolcastSensorSpec(
        "forecast_remaining_today_kwh",
        "solcast_forecast_remaining_today",
        "Forecast remaining today",
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:solar-power-clock",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
        include_forecast_attrs=True,
    ),
    SolcastSensorSpec(
        "forecast_this_hour_wh",
        "solcast_forecast_this_hour",
        "Forecast this hour",
        "Wh",
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
    ),
    SolcastSensorSpec(
        "forecast_next_hour_wh",
        "solcast_forecast_next_hour",
        "Forecast next hour",
        "Wh",
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
    ),
    SolcastSensorSpec(
        "forecast_next_x_hours_kwh",
        "solcast_forecast_next_x_hours",
        f"Forecast next {FORECAST_NEXT_X_HOURS} hours",
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
    ),
    SolcastSensorSpec(
        "peak_forecast_today_w",
        "solcast_peak_forecast_today",
        "Peak forecast today",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SolcastSensorSpec(
        "peak_forecast_tomorrow_w",
        "solcast_peak_forecast_tomorrow",
        "Peak forecast tomorrow",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SolcastSensorSpec(
        "peak_time_today",
        "solcast_peak_time_today",
        "Peak time today",
        None,
        "mdi:clock-outline",
        SensorDeviceClass.TIMESTAMP,
        None,
        is_timestamp=True,
    ),
    SolcastSensorSpec(
        "peak_time_tomorrow",
        "solcast_peak_time_tomorrow",
        "Peak time tomorrow",
        None,
        "mdi:clock-outline",
        SensorDeviceClass.TIMESTAMP,
        None,
        is_timestamp=True,
    ),
    SolcastSensorSpec(
        "power_now_w",
        "solcast_power_now",
        "Power now",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SolcastSensorSpec(
        "power_in_30_minutes_w",
        "solcast_power_in_30_minutes",
        "Power in 30 minutes",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SolcastSensorSpec(
        "power_in_1_hour_w",
        "solcast_power_in_1_hour",
        "Power in 1 hour",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
)


TARIFF_RATE_SENSORS: tuple[tuple[str, bool, str], ...] = (
    ("import", False, "Tariff import rate"),
    ("export", False, "Tariff export rate"),
    ("standing", True, "Tariff standing charge"),
)

OCTOPUS_CONSUMPTION_SENSORS: tuple[tuple[str, str, str, str, SensorDeviceClass | None, SensorStateClass | None], ...] = (
    ("half_hour", UnitOfEnergy.KILO_WATT_HOUR, "Octopus import (half-hour)", "mdi:flash", SensorDeviceClass.ENERGY, SensorStateClass.MEASUREMENT),
    ("today", UnitOfEnergy.KILO_WATT_HOUR, "Octopus import today", "mdi:home-import-outline", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL),
    ("greener_alignment", PERCENTAGE, "Octopus greener-night alignment", "mdi:leaf", None, SensorStateClass.MEASUREMENT),
)

GLOW_SENSORS: tuple[tuple[str, str, str, str, SensorDeviceClass | None, SensorStateClass | None], ...] = (
    ("import_power", UnitOfPower.KILO_WATT, "Glow grid import power", "mdi:transmission-tower-import", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    ("import_today", UnitOfEnergy.KILO_WATT_HOUR, "Glow grid import today", "mdi:home-import-outline", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    ("import_cumulative", UnitOfEnergy.KILO_WATT_HOUR, "Glow grid import total", "mdi:counter", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
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
    for spec in SOLCAST_FORECAST_SENSORS:
        entities.append(FoxessPlantSolcastForecastSensor(coordinator, entry, spec))
    for kind, per_day, name in TARIFF_RATE_SENSORS:
        entities.append(FoxessPlantTariffRateSensor(coordinator, entry, kind, per_day, name))
    for kind, unit, name, icon, device_class, state_class in OCTOPUS_CONSUMPTION_SENSORS:
        entities.append(
            FoxessPlantOctopusConsumptionSensor(
                coordinator, entry, kind, unit, name, icon, device_class, state_class
            )
        )
    for kind, unit, name, icon, device_class, state_class in GLOW_SENSORS:
        entities.append(
            FoxessPlantGlowSensor(
                coordinator, entry, kind, unit, name, icon, device_class, state_class
            )
        )
    async_add_entities(entities)


class FoxessPlantModeSensor(CoordinatorEntity[FoxessPlantCoordinator], SensorEntity):
    """Current plant control mode."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:solar-power"

    def __init__(self, coordinator: FoxessPlantCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = plant_device_info(entry)
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
        self._attr_device_info = plant_device_info(entry)
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


def _solcast_forecast_attributes(sc: dict[str, Any]) -> dict[str, Any]:
    detailed = sc.get("detailed_forecast") or []
    by_site = sc.get("detailed_forecast_by_site") or {}
    attrs: dict[str, Any] = {
        "detailed_forecast": detailed,
        "detailedForecast": detailed,
        "source": "foxess_plant_solcast",
        "pv_requests": sc.get("pv_requests") or [],
        "pv_forecast_periods": sc.get("pv_forecast_periods"),
        "last_fetch_at": sc.get("last_fetch_at"),
    }
    if isinstance(by_site, dict):
        attrs.update(by_site)
    return attrs


class FoxessPlantSolcastForecastSensor(CoordinatorEntity[FoxessPlantCoordinator], SensorEntity):
    """Native Solcast PV forecast sensors (ha-solcast-solar compatible set)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: FoxessPlantCoordinator,
        entry: ConfigEntry,
        spec: SolcastSensorSpec,
    ) -> None:
        super().__init__(coordinator)
        self._spec = spec
        self._attr_device_info = plant_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_{spec.unique_suffix}"
        self._attr_name = f"{entry.title} {spec.name}"
        self._attr_icon = spec.icon
        if spec.unit:
            self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class

    def _solcast(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("solcast") or {}

    def _raw_metric(self) -> Any:
        sc = self._solcast()
        raw = sc.get(self._spec.metric_key)
        if raw is not None:
            return raw
        rows = sc.get("detailed_forecast")
        if not isinstance(rows, list) or not rows:
            return None
        from .solcast_forecast_metrics import compute_forecast_metrics

        return compute_forecast_metrics(self.coordinator.hass, rows).get(self._spec.metric_key)

    def _coerce_native_value(self, raw: Any) -> float | datetime | None:
        if raw is None:
            return None
        if self._spec.is_timestamp:
            if isinstance(raw, datetime):
                return dt_util.as_utc(raw) if raw.tzinfo else raw.replace(tzinfo=dt_util.UTC)
            parsed = dt_util.parse_datetime(str(raw))
            return dt_util.as_utc(parsed) if parsed else None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        sc = self._solcast()
        if not sc.get("enabled") or not sc.get("api_key_set"):
            return False
        if not sc.get("pv_forecast_available"):
            return False
        return self._coerce_native_value(self._raw_metric()) is not None

    @property
    def native_value(self) -> float | datetime | None:
        return self._coerce_native_value(self._raw_metric())

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        sc = self._solcast()
        attrs: dict[str, Any] = {}
        if self._spec.include_forecast_attrs:
            attrs.update(_solcast_forecast_attributes(sc))
        if self._spec.metric_key == "forecast_next_x_hours_kwh":
            attrs["hours"] = sc.get("forecast_next_x_hours", FORECAST_NEXT_X_HOURS)
        return attrs or None


class FoxessPlantTariffRateSensor(CoordinatorEntity[FoxessPlantCoordinator], SensorEntity):
    """Plugin-owned tariff rate sensors (schedule, standing charge, future Agile API)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash-multiple"

    def __init__(
        self,
        coordinator: FoxessPlantCoordinator,
        entry: ConfigEntry,
        rate_kind: str,
        per_day: bool,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._rate_kind = rate_kind
        self._per_day = per_day
        self._entry = entry
        self._attr_device_info = plant_device_info(entry)
        self._attr_unique_id = tariff_sensor_unique_id(entry.entry_id, rate_kind)
        self._attr_name = f"{entry.title} {name}"
        self._minor_value: float | None = None
        self._band_index: int | None = None
        coordinator.register_tariff_rate_sensor(rate_kind, self)

    @property
    def native_unit_of_measurement(self) -> str:
        currency = normalize_tariff_currency(self.coordinator.plant.tariff.currency)
        return f"{currency}/day" if self._per_day else f"{currency}/kWh"

    @property
    def available(self) -> bool:
        return self._minor_value is not None

    @property
    def native_value(self) -> float | None:
        if self._minor_value is None:
            return None
        return minor_to_major(
            self._minor_value, self.coordinator.plant.tariff.currency
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {"source": "foxess_plant"}
        if self._band_index is not None:
            attrs["band_index"] = self._band_index
        return attrs

    def set_rate(self, minor_value: float | None, *, band_index: int | None = None) -> None:
        """Update stored rate; coordinator calls async_write after batching changes."""
        self._minor_value = minor_value
        self._band_index = band_index

    async def async_publish(self) -> None:
        """Write updated rate to Home Assistant state (recorder-friendly)."""
        self.async_write_ha_state()


class FoxessPlantOctopusConsumptionSensor(CoordinatorEntity[FoxessPlantCoordinator], SensorEntity):
    """Octopus smart-meter consumption — polled every 30 minutes for recorder history."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: FoxessPlantCoordinator,
        entry: ConfigEntry,
        kind: str,
        unit: str,
        name: str,
        icon: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
    ) -> None:
        super().__init__(coordinator)
        self._kind = kind
        self._entry = entry
        self._attr_device_info = plant_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_octopus_{kind}"
        self._attr_name = f"{entry.title} {name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._value: float | None = None
        coordinator.register_octopus_consumption_sensor(kind, self)

    @property
    def available(self) -> bool:
        from .octopus_greener import octopus_tariff_enabled

        if not octopus_tariff_enabled(self.coordinator.plant.tariff):
            return False
        return self._value is not None

    @property
    def native_value(self) -> float | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {"source": "octopus_api"}
        fetched = self.coordinator._octopus_consumption_data.get("last_fetch_at")
        if fetched:
            attrs["last_fetch_at"] = fetched
        return attrs

    def set_value(self, value: float | None) -> None:
        self._value = value

    async def async_publish(self) -> None:
        self.async_write_ha_state()


class FoxessPlantGlowSensor(CoordinatorEntity[FoxessPlantCoordinator], SensorEntity):
    """Live Glow smart-meter readings for grid import (electricity only)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: FoxessPlantCoordinator,
        entry: ConfigEntry,
        kind: str,
        unit: str,
        name: str,
        icon: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
    ) -> None:
        super().__init__(coordinator)
        self._kind = kind
        self._entry = entry
        self._attr_device_info = plant_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_glow_{kind}"
        self._attr_name = f"{entry.title} {name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._value: float | None = None
        coordinator.register_glow_sensor(kind, self)

    @property
    def available(self) -> bool:
        if not self.coordinator.plant.glow.enabled:
            return False
        return self._value is not None

    @property
    def native_value(self) -> float | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        live = self.coordinator._glow_live
        return {
            "source": live.get("source") or "glow",
            "device_mac": live.get("device_mac") or self.coordinator.plant.glow.device_mac,
            "timestamp": live.get("timestamp") or self.coordinator.plant.glow.last_mqtt_at,
            "mpan": live.get("mpan"),
        }

    def set_value(self, value: float | None) -> None:
        self._value = value

    async def async_publish(self) -> None:
        self.async_write_ha_state()

