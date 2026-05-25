"""WebSocket API for the Fox Plant panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

WS_TYPE_PLANT_STATE = "foxess_plant/plant_state"
WS_TYPE_PLANT_LIST = "foxess_plant/plant_list"


def _plant_summary(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    data = hass.data[DOMAIN][entry_id]
    coordinator = data["coordinator"]
    return coordinator.get_plant_state()


@callback
def async_register_ws_handlers(hass: HomeAssistant) -> None:
    """Register websocket commands for the panel."""

    @websocket_api.websocket_command({vol.Required("type"): WS_TYPE_PLANT_LIST})
    @websocket_api.async_response
    async def ws_plant_list(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        plants = []
        for entry_id in hass.data.get(DOMAIN, {}):
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
        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            connection.send_error(msg["id"], "not_found", "No plants configured")
            return
        if plant_id is None:
            if len(domain_data) == 1:
                plant_id = next(iter(domain_data))
            else:
                connection.send_error(msg["id"], "invalid_info", "plant_id required")
                return
        if plant_id not in domain_data:
            connection.send_error(msg["id"], "not_found", f"Plant {plant_id} not found")
            return
        connection.send_result(msg["id"], _plant_summary(hass, plant_id))

    websocket_api.async_register_command(hass, ws_plant_list)
    websocket_api.async_register_command(hass, ws_plant_state)
