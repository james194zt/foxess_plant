"""WebSocket API for the Fox Plant panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, STORM_ALERT_PROVIDER_GOOGLE
from .panel_config import list_trigger_candidates

WS_TYPE_PLANT_STATE = "foxess_plant/plant_state"
WS_TYPE_PLANT_LIST = "foxess_plant/plant_list"
WS_TYPE_TRIGGER_CANDIDATES = "foxess_plant/trigger_candidates"
WS_TYPE_UPDATE_STORM_PREP = "foxess_plant/update_storm_prep"
WS_TYPE_SET_SOC_LIMITS = "foxess_plant/set_soc_limits"

PERIOD_SCHEMA = vol.Schema(
    {
        vol.Required("enable_force_charge"): cv.boolean,
        vol.Required("enable_charge_from_grid"): cv.boolean,
        vol.Optional("start", default="00:00"): cv.string,
        vol.Optional("end", default="00:00"): cv.string,
    }
)


def _get_coordinator(hass: HomeAssistant, plant_id: str | None):
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data:
        return None, "not_found", "No plants configured"
    if plant_id is None:
        if len(domain_data) == 1:
            plant_id = next(iter(domain_data))
        else:
            return None, "invalid_info", "plant_id required"
    if plant_id not in domain_data:
        return None, "not_found", f"Plant {plant_id} not found"
    return domain_data[plant_id]["coordinator"], None, None


def _plant_summary(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    data = hass.data[DOMAIN][entry_id]
    coordinator = data["coordinator"]
    return coordinator.get_plant_state()


@callback
def async_register_ws_handlers(hass: HomeAssistant) -> None:
    """Register websocket commands for the panel."""
    if hass.data.get("_foxess_plant_ws_registered"):
        return

    @websocket_api.websocket_command({vol.Required("type"): WS_TYPE_PLANT_LIST})
    @websocket_api.async_response
    async def ws_plant_list(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        plants = []
        for entry_id in hass.data.get(DOMAIN, {}):
            if not isinstance(hass.data[DOMAIN].get(entry_id), dict):
                continue
            try:
                summary = _plant_summary(hass, entry_id)
            except KeyError:
                continue
            plants.append(
                {
                    "entry_id": entry_id,
                    "title": summary.get("title"),
                    "mode": summary.get("mode"),
                    "control_active": summary.get("control_active"),
                }
            )
        connection.send_result(msg["id"], {"plants": plants})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_PLANT_STATE,
            vol.Optional("plant_id"): str,
        }
    )
    @websocket_api.async_response
    async def ws_plant_state(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        plant_id = msg.get("plant_id")
        coordinator, err_code, err_msg = _get_coordinator(hass, plant_id)
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        connection.send_result(msg["id"], _plant_summary(hass, coordinator.config_entry.entry_id))

    @websocket_api.websocket_command({vol.Required("type"): WS_TYPE_TRIGGER_CANDIDATES})
    @websocket_api.async_response
    async def ws_trigger_candidates(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        connection.send_result(msg["id"], list_trigger_candidates(hass))

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_UPDATE_STORM_PREP,
            vol.Optional("plant_id"): str,
            vol.Required("enabled"): cv.boolean,
            vol.Optional("trigger_entities", default=[]): [cv.entity_id],
            vol.Required("charge_periods"): [PERIOD_SCHEMA],
            vol.Optional("target_max_soc"): vol.Any(vol.Coerce(float), None),
            vol.Optional("alert_provider"): vol.In([STORM_ALERT_PROVIDER_GOOGLE]),
            vol.Optional("google_weather_entry_id"): str,
            vol.Optional("use_forecast_lead"): cv.boolean,
            vol.Optional("forecast_lead_hours"): vol.All(vol.Coerce(int), vol.Range(min=1, max=48)),
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_update_storm_prep(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        target = msg.get("target_max_soc")
        await coordinator.async_save_storm_prep(
            enabled=msg["enabled"],
            trigger_entities=msg.get("trigger_entities") or [],
            charge_periods=msg["charge_periods"],
            target_max_soc=float(target) if target is not None else None,
            alert_provider=msg.get("alert_provider"),
            google_weather_entry_id=msg.get("google_weather_entry_id"),
            use_forecast_lead=msg.get("use_forecast_lead"),
            forecast_lead_hours=msg.get("forecast_lead_hours"),
        )
        connection.send_result(msg["id"], coordinator.get_plant_state())

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_SET_SOC_LIMITS,
            vol.Optional("plant_id"): str,
            vol.Required("min_soc"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
            vol.Required("min_soc_on_grid"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
            vol.Required("max_soc"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_set_soc_limits(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        await coordinator.async_set_soc_limits(
            msg["min_soc"],
            msg["min_soc_on_grid"],
            msg["max_soc"],
        )
        connection.send_result(msg["id"], coordinator.get_plant_state())

    websocket_api.async_register_command(hass, ws_plant_list)
    websocket_api.async_register_command(hass, ws_plant_state)
    websocket_api.async_register_command(hass, ws_trigger_candidates)
    websocket_api.async_register_command(hass, ws_update_storm_prep)
    websocket_api.async_register_command(hass, ws_set_soc_limits)
    hass.data["_foxess_plant_ws_registered"] = True
