"""Register foxess_plant services."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .models import ChargePeriodConfig

_LOGGER = logging.getLogger(__name__)

PERIOD_SCHEMA = {
    vol.Required("enable_force_charge"): cv.boolean,
    vol.Required("enable_charge_from_grid"): cv.boolean,
    vol.Optional("start", default="00:00"): cv.string,
    vol.Optional("end", default="00:00"): cv.string,
}


def _get_coordinator(hass: HomeAssistant, call: ServiceCall):
    plant_id = call.data.get("plant_id")
    domain_data = hass.data.get(DOMAIN, {})
    if plant_id:
        if plant_id not in domain_data:
            raise HomeAssistantError(f"Plant {plant_id} not found")
        return domain_data[plant_id]["coordinator"]
    if len(domain_data) == 1:
        return next(iter(domain_data.values()))["coordinator"]
    raise HomeAssistantError("plant_id required when multiple plants are configured")


def _periods_from_service(data: list[dict[str, Any]]) -> list[ChargePeriodConfig]:
    return [ChargePeriodConfig.from_dict(p) for p in data]


def register_services(hass: HomeAssistant) -> None:
    """Register plant control services for automations and Node-RED."""

    async def reload_panel(call: ServiceCall) -> None:
        from .panel import _PANEL_DISK_INFO_KEY, async_register_panel

        hass.data.pop(_PANEL_DISK_INFO_KEY, None)
        await async_register_panel(hass)
        _LOGGER.info("Fox Plant panel reloaded via foxess_plant.reload_panel service")

    if not hass.services.has_service(DOMAIN, "reload_panel"):
        hass.services.async_register(
            DOMAIN,
            "reload_panel",
            reload_panel,
            schema=vol.Schema({vol.Optional("plant_id"): cv.string}),
        )

    if hass.services.has_service(DOMAIN, "apply_baseline"):
        return

    async def apply_baseline(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_apply_baseline()

    async def apply_desired(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_apply_desired()

    async def sync_schedule_from_inverter(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_sync_schedule_from_inverter()

    async def reapply_schedule(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_reapply_schedule()

    async def set_charge_period(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        period = ChargePeriodConfig(
            enable_force_charge=call.data["enable_force_charge"],
            enable_charge_from_grid=call.data["enable_charge_from_grid"],
            start=call.data.get("start", "00:00"),
            end=call.data.get("end", "00:00"),
        )
        await coord.async_set_charge_period(
            call.data["charge_period"],
            period,
            apply_now=call.data.get("apply_now", True),
        )

    async def set_charge_periods(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        periods = _periods_from_service(call.data["charge_periods"])
        as_override = call.data.get("as_override", False)
        if as_override:
            await coord.async_set_override_periods(
                periods,
                call.data.get("mode", "override"),
                call.data.get("reason", "service"),
            )
        else:
            await coord.async_set_baseline_periods(
                periods,
                apply_now=call.data.get("apply_now", True),
            )

    async def save_charge_schedule(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        periods = _periods_from_service(call.data["charge_periods"])
        await coord.async_save_charge_schedule(periods)

    async def arm_storm_prep(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        periods = (
            _periods_from_service(call.data["charge_periods"])
            if "charge_periods" in call.data
            else None
        )
        await coord.async_arm_storm_prep(
            periods,
            reason=call.data.get("reason", "storm_prep"),
        )

    async def disarm_storm_prep(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_disarm_override()

    async def take_control(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_take_control()

    async def release_control(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_release_control()

    async def get_plant_state(call: ServiceCall) -> dict[str, Any]:
        return _get_coordinator(hass, call).get_plant_state()

    async def set_tariff_mode(call: ServiceCall) -> None:
        await _get_coordinator(hass, call).async_set_tariff_mode(call.data["mode"])

    async def set_tariff_profile(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        mode_name = call.data["mode"]
        periods = _periods_from_service(call.data["charge_periods"])
        await coord.async_set_tariff_profile(mode_name, periods)
        if call.data.get("apply_now", False):
            await coord.async_set_tariff_mode(mode_name)

    plant_id = vol.Optional("plant_id")

    hass.services.async_register(
        DOMAIN,
        "apply_baseline",
        apply_baseline,
        schema=vol.Schema({plant_id: cv.string}),
        supports_response=False,
    )
    hass.services.async_register(
        DOMAIN,
        "apply_desired",
        apply_desired,
        schema=vol.Schema({plant_id: cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        "sync_schedule_from_inverter",
        sync_schedule_from_inverter,
        schema=vol.Schema({plant_id: cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        "reapply_schedule",
        reapply_schedule,
        schema=vol.Schema({plant_id: cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        "set_charge_period",
        set_charge_period,
        schema=vol.Schema(
            {
                plant_id: cv.string,
                vol.Required("charge_period"): vol.All(int, vol.Range(min=1, max=2)),
                **PERIOD_SCHEMA,
                vol.Optional("apply_now", default=True): cv.boolean,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "set_charge_periods",
        set_charge_periods,
        schema=vol.Schema(
            {
                plant_id: cv.string,
                vol.Required("charge_periods"): [vol.Schema(PERIOD_SCHEMA)],
                vol.Optional("as_override", default=False): cv.boolean,
                vol.Optional("mode", default="override"): cv.string,
                vol.Optional("reason", default="service"): cv.string,
                vol.Optional("apply_now", default=True): cv.boolean,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "save_charge_schedule",
        save_charge_schedule,
        schema=vol.Schema(
            {
                plant_id: cv.string,
                vol.Required("charge_periods"): [vol.Schema(PERIOD_SCHEMA)],
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "arm_storm_prep",
        arm_storm_prep,
        schema=vol.Schema(
            {
                plant_id: cv.string,
                vol.Optional("charge_periods"): [vol.Schema(PERIOD_SCHEMA)],
                vol.Optional("reason", default="storm_prep"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "disarm_storm_prep",
        disarm_storm_prep,
        schema=vol.Schema({plant_id: cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        "take_control",
        take_control,
        schema=vol.Schema({plant_id: cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        "release_control",
        release_control,
        schema=vol.Schema({plant_id: cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        "get_plant_state",
        get_plant_state,
        schema=vol.Schema({plant_id: cv.string}),
        supports_response=True,
    )
    hass.services.async_register(
        DOMAIN,
        "set_tariff_mode",
        set_tariff_mode,
        schema=vol.Schema(
            {
                plant_id: cv.string,
                vol.Required("mode"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "set_tariff_profile",
        set_tariff_profile,
        schema=vol.Schema(
            {
                plant_id: cv.string,
                vol.Required("mode"): cv.string,
                vol.Required("charge_periods"): [vol.Schema(PERIOD_SCHEMA)],
                vol.Optional("apply_now", default=False): cv.boolean,
            }
        ),
    )
