"""Register FoxESS Plant Lovelace card resources (storage-mode dashboards)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from .const import PANEL_STATIC_URL

_LOGGER = logging.getLogger(__name__)

_FLOW_SCENE_CARD_FILE = "fox-flow-scene-card.js"
_LOVELACE_REGISTER_KEY = "_foxess_plant_lovelace_cards_registered"


def _integration_version() -> str:
    manifest = Path(__file__).parent / "manifest.json"
    with manifest.open(encoding="utf-8") as handle:
        return json.load(handle).get("version", "0")


def flow_scene_card_resource_url() -> str:
    return f"{PANEL_STATIC_URL}/{_FLOW_SCENE_CARD_FILE}?v={_integration_version()}"


def _resource_path(url: str) -> str:
    return url.split("?", 1)[0]


def _resource_version(url: str) -> str:
    if "?v=" not in url:
        return "0"
    return url.rsplit("?v=", 1)[-1]


async def async_register_lovelace_cards(hass: HomeAssistant) -> None:
    """Add or update the Fox Flow Scene card module in Lovelace resources."""
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        async def _retry(_now: Any) -> None:
            await async_register_lovelace_cards(hass)

        async_call_later(hass, 5, _retry)
        return
    if getattr(lovelace, "mode", "yaml") != "storage":
        _LOGGER.debug(
            "Lovelace YAML mode: add %s manually under dashboard resources if needed",
            flow_scene_card_resource_url(),
        )
        return

    async def _wait_for_resources(_now: Any) -> None:
        resources = getattr(lovelace, "resources", None)
        if resources is None or not getattr(resources, "loaded", False):
            async_call_later(hass, 5, _wait_for_resources)
            return
        await _async_upsert_flow_scene_resource(hass, lovelace)

    await _wait_for_resources(None)


async def _async_upsert_flow_scene_resource(hass: HomeAssistant, lovelace: Any) -> None:
    url = flow_scene_card_resource_url()
    path = _resource_path(url)
    version = _integration_version()
    existing = [
        item
        for item in lovelace.resources.async_items()
        if _resource_path(item.get("url", "")) == path
    ]
    payload = {"res_type": "module", "url": url}
    if existing:
        current = existing[0]
        if _resource_version(current.get("url", "")) != version:
            _LOGGER.info("Updating Fox Flow Scene Lovelace card to v%s", version)
            await lovelace.resources.async_update_item(current["id"], payload)
    else:
        _LOGGER.info("Registering Fox Flow Scene Lovelace card v%s", version)
        await lovelace.resources.async_create_item(payload)
    hass.data[_LOVELACE_REGISTER_KEY] = version
