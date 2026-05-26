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
    CONF_BASELINE_PERIODS,
    CONF_CONTROL,
    CONF_DEVICE_ID,
    CONF_FORECAST_PREP,
    CONF_OUTAGE_PREP,
    CONF_STORM_PREP,
    CONF_TARIFF_MODES,
    DEFAULT_BASELINE_PERIODS,
    DEFAULT_CONTROL,
    DOMAIN,
    MODBUS_DOMAIN,
)
from .discovery import (
    discover_entity_map,
    inverter_target_from_device,
    is_foxess_modbus_device,
    missing_charge_period_entities,
)
from .models import ChargePeriodConfig, ControlConfig, PlantConfig

_LOGGER = logging.getLogger(__name__)

MENU_BASELINE = "baseline"
MENU_STORM = "storm_prep"
MENU_OUTAGE = "outage_prep"
MENU_FORECAST = "forecast_prep"
MENU_TARIFF = "tariff"


def _device_selector() -> selector.DeviceSelector:
    return selector.DeviceSelector(
        config=selector.DeviceSelectorConfig(integration=MODBUS_DOMAIN)
    )


def _entity_multi_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        config=selector.EntitySelectorConfig(multiple=True)
    )


def _optional_max_soc_schema(default: float | None):
    """HA form schema for optional max SoC (empty = not set)."""
    if default is None:
        return vol.Optional("target_max_soc", default="")
    return vol.Optional("target_max_soc", default=default)


def _period_schema(prefix: str, period: ChargePeriodConfig) -> dict:
    return {
        vol.Required(f"{prefix}_force", default=period.enable_force_charge): bool,
        vol.Required(f"{prefix}_grid", default=period.enable_charge_from_grid): bool,
        vol.Required(f"{prefix}_start", default=period.start): str,
        vol.Required(f"{prefix}_end", default=period.end): str,
    }


def _periods_from_form(data: dict[str, Any], p1_prefix: str, p2_prefix: str) -> list[dict[str, Any]]:
    return [
        ChargePeriodConfig(
            enable_force_charge=data[f"{p1_prefix}_force"],
            enable_charge_from_grid=data[f"{p1_prefix}_grid"],
            start=data[f"{p1_prefix}_start"],
            end=data[f"{p1_prefix}_end"],
        ).to_dict(),
        ChargePeriodConfig(
            enable_force_charge=data[f"{p2_prefix}_force"],
            enable_charge_from_grid=data[f"{p2_prefix}_grid"],
            start=data[f"{p2_prefix}_start"],
            end=data[f"{p2_prefix}_end"],
        ).to_dict(),
    ]


class FoxessPlantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._device_id: str | None = None
        self._inverter_target: str | None = None
        self._entity_map: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input.get(CONF_DEVICE_ID)
            if not device_id:
                errors["base"] = "invalid_device"
            else:
                try:
                    device = await self._validate_device(self.hass, device_id)
                except HomeAssistantError as err:
                    _LOGGER.warning("Device validation failed for %s: %s", device_id, err)
                    errors["base"] = "invalid_device"
                else:
                    self._device_id = device_id
                    self._inverter_target = inverter_target_from_device(device)
                    self._entity_map = discover_entity_map(self.hass, device_id)
                    missing = missing_charge_period_entities(self._entity_map)
                    if missing:
                        _LOGGER.warning("Missing charge period entities: %s", missing)
                    return await self.async_step_confirm()

        schema = vol.Schema({vol.Required(CONF_DEVICE_ID): _device_selector()})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _validate_device(self, hass: HomeAssistant, device_id: str) -> dr.DeviceEntry:
        device_reg = dr.async_get(hass)
        device = device_reg.async_get(device_id)
        if device is None:
            raise HomeAssistantError("Device not found")
        if not is_foxess_modbus_device(device):
            raise HomeAssistantError("Not a foxess_modbus device")
        return device

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        assert self._device_id is not None
        assert self._inverter_target is not None
        device_reg = dr.async_get(self.hass)
        device = device_reg.async_get(self._device_id)
        title = device.name or "FoxESS Plant"

        if user_input is not None:
            baseline = [
                ChargePeriodConfig.from_dict(p) for p in DEFAULT_BASELINE_PERIODS
            ]
            plant = PlantConfig(
                device_id=self._device_id,
                inverter_target=self._inverter_target,
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
    """Options flow for baseline, prep policies, and tariff profiles."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    def _plant(self) -> PlantConfig:
        return PlantConfig.from_entry_data(self.config_entry.data)

    def _update_data(self, data: dict[str, Any]) -> None:
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]["coordinator"]
        coordinator.update_plant_config(PlantConfig.from_entry_data(data))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        try:
            return self.async_show_menu(
                step_id="init",
                menu_options=[
                    MENU_BASELINE,
                    MENU_STORM,
                    MENU_OUTAGE,
                    MENU_FORECAST,
                    MENU_TARIFF,
                ],
            )
        except Exception as err:
            _LOGGER.exception("FoxESS Plant options menu failed: %s", err)
            return self.async_show_form(
                step_id="init",
                errors={"base": "unknown"},
                description_placeholders={"error": str(err)},
            )

    async def async_step_baseline(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        plant = self._plant()

        if user_input is not None:
            data = dict(self.config_entry.data)
            data[CONF_CONTROL] = {
                "exclusive": user_input["exclusive"],
                "drift_check_interval": user_input["drift_check_interval"],
                "on_drift": user_input["on_drift"],
            }
            data[CONF_BASELINE_PERIODS] = _periods_from_form(user_input, "p1", "p2")
            self._update_data(data)
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]["coordinator"]
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
                **_period_schema("p1", p1),
                **_period_schema("p2", p2),
            }
        )
        return self.async_show_form(step_id="baseline", data_schema=schema)

    async def async_step_storm_prep(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        plant = self._plant()
        cfg = plant.storm_prep

        if user_input is not None:
            data = dict(self.config_entry.data)
            target = user_input.get("target_max_soc")
            data[CONF_STORM_PREP] = {
                "enabled": user_input["enabled"],
                "trigger_entities": user_input.get("trigger_entities") or [],
                "charge_periods": _periods_from_form(user_input, "p1", "p2"),
                "target_max_soc": float(target) if target not in (None, "") else None,
            }
            self._update_data(data)
            return self.async_create_entry(title="", data={})

        p1 = cfg.charge_periods[0] if cfg.charge_periods else ChargePeriodConfig()
        p2 = cfg.charge_periods[1] if len(cfg.charge_periods) > 1 else ChargePeriodConfig()
        schema = vol.Schema(
            {
                vol.Required("enabled", default=cfg.enabled): bool,
                vol.Optional("trigger_entities", default=cfg.trigger_entities): _entity_multi_selector(),
                _optional_max_soc_schema(cfg.target_max_soc): vol.Any(
                    vol.Coerce(float), "", None
                ),
                **_period_schema("p1", p1),
                **_period_schema("p2", p2),
            }
        )
        return self.async_show_form(step_id="storm_prep", data_schema=schema)

    async def async_step_outage_prep(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        plant = self._plant()
        cfg = plant.outage_prep

        if user_input is not None:
            data = dict(self.config_entry.data)
            target = user_input.get("target_max_soc")
            data[CONF_OUTAGE_PREP] = {
                "enabled": user_input["enabled"],
                "trigger_entities": user_input.get("trigger_entities") or [],
                "charge_periods": _periods_from_form(user_input, "p1", "p2"),
                "target_max_soc": float(target) if target not in (None, "") else None,
            }
            self._update_data(data)
            return self.async_create_entry(title="", data={})

        p1 = cfg.charge_periods[0] if cfg.charge_periods else ChargePeriodConfig()
        p2 = cfg.charge_periods[1] if len(cfg.charge_periods) > 1 else ChargePeriodConfig()
        schema = vol.Schema(
            {
                vol.Required("enabled", default=cfg.enabled): bool,
                vol.Optional("trigger_entities", default=cfg.trigger_entities): _entity_multi_selector(),
                _optional_max_soc_schema(cfg.target_max_soc): vol.Any(
                    vol.Coerce(float), "", None
                ),
                **_period_schema("p1", p1),
                **_period_schema("p2", p2),
            }
        )
        return self.async_show_form(step_id="outage_prep", data_schema=schema)

    async def async_step_forecast_prep(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        plant = self._plant()
        cfg = plant.forecast_prep

        if user_input is not None:
            data = dict(self.config_entry.data)
            target = user_input.get("target_max_soc")
            data[CONF_FORECAST_PREP] = {
                "enabled": user_input["enabled"],
                "forecast_entity": user_input.get("forecast_entity"),
                "threshold_kwh": float(user_input["threshold_kwh"]),
                "charge_periods": _periods_from_form(user_input, "p1", "p2"),
                "target_max_soc": float(target) if target not in (None, "") else None,
            }
            self._update_data(data)
            return self.async_create_entry(title="", data={})

        p1 = cfg.charge_periods[0] if cfg.charge_periods else ChargePeriodConfig()
        p2 = cfg.charge_periods[1] if len(cfg.charge_periods) > 1 else ChargePeriodConfig()
        schema = vol.Schema(
            {
                vol.Required("enabled", default=cfg.enabled): bool,
                vol.Optional("forecast_entity", default=cfg.forecast_entity): selector.EntitySelector(),
                vol.Required("threshold_kwh", default=cfg.threshold_kwh): vol.All(
                    vol.Coerce(float), vol.Range(min=0.1, max=100)
                ),
                _optional_max_soc_schema(cfg.target_max_soc): vol.Any(
                    vol.Coerce(float), "", None
                ),
                **_period_schema("p1", p1),
                **_period_schema("p2", p2),
            }
        )
        return self.async_show_form(step_id="forecast_prep", data_schema=schema)

    async def async_step_tariff(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        plant = self._plant()
        cheap = plant.tariff_modes.get("cheap_import", [])
        p1 = ChargePeriodConfig.from_dict(cheap[0]) if cheap else ChargePeriodConfig(
            enable_force_charge=True,
            enable_charge_from_grid=True,
            start="00:30",
            end="05:00",
        )
        p2 = ChargePeriodConfig.from_dict(cheap[1]) if len(cheap) > 1 else ChargePeriodConfig()

        if user_input is not None:
            data = dict(self.config_entry.data)
            tariff_modes = dict(data.get(CONF_TARIFF_MODES, {}))
            tariff_modes["cheap_import"] = _periods_from_form(user_input, "p1", "p2")
            data[CONF_TARIFF_MODES] = tariff_modes
            self._update_data(data)
            return self.async_create_entry(title="", data={})

        schema = vol.Schema(
            {
                **_period_schema("p1", p1),
                **_period_schema("p2", p2),
            }
        )
        return self.async_show_form(step_id="tariff", data_schema=schema)
