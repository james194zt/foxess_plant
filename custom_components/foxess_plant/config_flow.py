"""Config flow for foxess_plant."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .const import (
    CONF_CONTROL,
    CONF_DEVICE_ID,
    DEFAULT_BASELINE_PERIODS,
    DEFAULT_CONTROL,
    DOMAIN,
    MODBUS_DOMAIN,
)
from .discovery import discover_entity_map, missing_charge_period_entities
from .models import ChargePeriodConfig, ControlConfig, PlantConfig

_LOGGER = logging.getLogger(__name__)


def _device_selector() -> selector.DeviceSelector:
    return selector.DeviceSelector(
        config=selector.DeviceSelectorConfig(integration=MODBUS_DOMAIN)
    )


class FoxessPlantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._device_id: str | None = None
        self._entity_map: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            try:
                await self._validate_device(self.hass, device_id)
            except HomeAssistantError:
                errors["base"] = "invalid_device"
            else:
                self._device_id = device_id
                self._entity_map = discover_entity_map(self.hass, device_id)
                missing = missing_charge_period_entities(self._entity_map)
                if missing:
                    _LOGGER.warning("Missing charge period entities: %s", missing)
                return await self.async_step_confirm()

        schema = vol.Schema({vol.Required(CONF_DEVICE_ID): _device_selector()})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _validate_device(self, hass: HomeAssistant, device_id: str) -> None:
        device_reg = dr.async_get(hass)
        device = device_reg.async_get(device_id)
        if device is None:
            raise HomeAssistantError("Device not found")
        if MODBUS_DOMAIN not in device.identifiers:
            raise HomeAssistantError("Not a foxess_modbus device")

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        assert self._device_id is not None
        device_reg = dr.async_get(self.hass)
        device = device_reg.async_get(self._device_id)
        title = device.name or "FoxESS Plant"

        if user_input is not None:
            baseline = [
                ChargePeriodConfig.from_dict(p) for p in DEFAULT_BASELINE_PERIODS
            ]
            plant = PlantConfig(
                device_id=self._device_id,
                inverter_target=self._device_id,
                entity_map=self._entity_map,
                baseline_periods=baseline,
                control=ControlConfig.from_dict(DEFAULT_CONTROL),
            )
            await self.async_set_unique_id(self._device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=title,
                data=plant.to_entry_data(),
            )

        missing = missing_charge_period_entities(self._entity_map)
        description_placeholders = {
            "device": title,
            "entities": "\n".join(
                f"- {k}: {v}" for k, v in sorted(self._entity_map.items())
            )
            or "(none discovered)",
            "missing": ", ".join(missing) if missing else "none",
        }
        return self.async_show_form(
            step_id="confirm",
            description_placeholders=description_placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return FoxessPlantOptionsFlow(config_entry)


class FoxessPlantOptionsFlow(config_entries.OptionsFlow):
    """Options flow for baseline periods and control settings."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        plant = PlantConfig.from_entry_data(self.config_entry.data)

        if user_input is not None:
            data = dict(self.config_entry.data)
            data[CONF_CONTROL] = {
                "exclusive": user_input["exclusive"],
                "drift_check_interval": user_input["drift_check_interval"],
                "on_drift": user_input["on_drift"],
            }
            p1 = ChargePeriodConfig(
                enable_force_charge=user_input["p1_force"],
                enable_charge_from_grid=user_input["p1_grid"],
                start=user_input["p1_start"],
                end=user_input["p1_end"],
            )
            p2 = ChargePeriodConfig(
                enable_force_charge=user_input["p2_force"],
                enable_charge_from_grid=user_input["p2_grid"],
                start=user_input["p2_start"],
                end=user_input["p2_end"],
            )
            data[CONF_BASELINE_PERIODS] = [p1.to_dict(), p2.to_dict()]
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]["coordinator"]
            coordinator.update_plant_config(PlantConfig.from_entry_data(data))
            await coordinator.async_apply_baseline()
            return self.async_create_entry(title="", data={})

        p1 = plant.baseline_periods[0] if plant.baseline_periods else ChargePeriodConfig()
        p2 = (
            plant.baseline_periods[1]
            if len(plant.baseline_periods) > 1
            else ChargePeriodConfig()
        )
        schema = vol.Schema(
            {
                vol.Required("exclusive", default=plant.control.exclusive): bool,
                vol.Required(
                    "drift_check_interval",
                    default=plant.control.drift_check_interval,
                ): vol.All(int, vol.Range(min=60, max=3600)),
                vol.Required("on_drift", default=plant.control.on_drift): vol.In(
                    ["reapply", "alert", "ignore"]
                ),
                vol.Required("p1_force", default=p1.enable_force_charge): bool,
                vol.Required("p1_grid", default=p1.enable_charge_from_grid): bool,
                vol.Required("p1_start", default=p1.start): str,
                vol.Required("p1_end", default=p1.end): str,
                vol.Required("p2_force", default=p2.enable_force_charge): bool,
                vol.Required("p2_grid", default=p2.enable_charge_from_grid): bool,
                vol.Required("p2_start", default=p2.start): str,
                vol.Required("p2_end", default=p2.end): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
