"""Local MQTT listener for Hildebrand Glow IHD smart-meter broadcasts."""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from homeassistant.core import HomeAssistant, callback

from .glow_grid import normalize_glow_device_id, parse_glow_electricity_payload

_LOGGER = logging.getLogger(__name__)

GlowMqttCallback = Callable[[dict[str, Any], str], Awaitable[None] | None]


async def async_subscribe_glow_mqtt(
    hass: HomeAssistant,
    *,
    topic_prefix: str,
    device_id: str,
    on_electricity: GlowMqttCallback,
    on_state: GlowMqttCallback | None = None,
) -> Callable[[], None]:
    """Subscribe to Glow IHD MQTT topics; returns an unsubscribe callback."""
    from homeassistant.components import mqtt
    from homeassistant.components.mqtt.models import ReceiveMessage

    prefix = str(topic_prefix or "glow").strip().replace("#", "").replace(" ", "")
    target = normalize_glow_device_id(device_id)
    data_topic = f"{prefix}/#"

    @callback
    async def _message_received(message: ReceiveMessage) -> None:
        topic = message.topic
        parts = topic.split("/")
        if len(parts) < 3 or parts[0] != prefix:
            return
        mac = normalize_glow_device_id(parts[1])
        if target != "+" and mac != target:
            return
        try:
            payload = json.loads(message.payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            _LOGGER.debug("Glow MQTT ignored non-JSON on %s", topic)
            return
        if not isinstance(payload, dict):
            return
        suffix = parts[-1].lower()
        if suffix == "electricitymeter" or topic.endswith("/SENSOR/electricitymeter"):
            parsed = parse_glow_electricity_payload(payload, source="glow_mqtt")
            if parsed:
                await _dispatch(on_electricity, parsed, mac)
        elif suffix == "state" and on_state is not None:
            await _dispatch(on_state, payload, mac)

    unsub = await mqtt.async_subscribe(hass, data_topic, _message_received, 1)
    _LOGGER.debug("Glow MQTT subscribed to %s (device=%s)", data_topic, target)

    @callback
    def _unsubscribe() -> None:
        unsub()

    return _unsubscribe


async def _dispatch(callback: GlowMqttCallback, payload: dict[str, Any], device_mac: str) -> None:
    try:
        result = callback(payload, device_mac)
        if result is not None:
            await result
    except Exception:
        _LOGGER.exception("Glow MQTT callback failed for %s", device_mac)


def mqtt_broker_configured(hass: HomeAssistant) -> bool:
    """True when the MQTT integration is loaded in Home Assistant."""
    return "mqtt" in hass.config.components
