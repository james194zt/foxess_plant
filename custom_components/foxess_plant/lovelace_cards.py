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
_MAX_LOVELACE_RETRIES = 24


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


def _lovelace_mode(lovelace: Any) -> str | None:
    mode = getattr(lovelace, "mode", None)
    if mode is not None:
        return mode
    if getattr(lovelace, "yaml_mode", False):
        return "yaml"
    return "storage"


def _can_register_storage_resources(lovelace: Any) -> bool:
    resources = getattr(lovelace, "resources", None)
    return resources is not None and hasattr(resources, "async_create_item")


async def _async_ensure_resources_loaded(resources: Any) -> None:
    """Load persisted resources before list/create (avoids wiping storage)."""
    if getattr(resources, "loaded", False):
        return
    if hasattr(resources, "async_get_info"):
        await resources.async_get_info()
        return
    if hasattr(resources, "async_load"):
        await resources.async_load()
        if hasattr(resources, "loaded"):
            resources.loaded = True


def _register_frontend_module(hass: HomeAssistant, url: str) -> None:
    """Load card JS globally (required for YAML dashboards and the card picker)."""
    from homeassistant.components.frontend import add_extra_js_url

    add_extra_js_url(hass, url)
    _LOGGER.info("Fox Flow Scene card module registered for frontend: %s", url)


async def async_register_lovelace_cards(hass: HomeAssistant, *, _retry: int = 0) -> None:
    """Add or update the Fox Flow Scene card module in Lovelace resources."""
    version = _integration_version()
    url = flow_scene_card_resource_url()

    # Always inject as a frontend module so YAML dashboards and the card picker
    # can load customCards even when lovelace resource_mode is yaml.
    _register_frontend_module(hass, url)

    if hass.data.get(_LOVELACE_REGISTER_KEY) == version:
        return

    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        if _retry >= _MAX_LOVELACE_RETRIES:
            _LOGGER.warning(
                "Lovelace component not ready; storage resource not updated. "
                "The card should still load via the frontend module URL %s",
                url,
            )
            hass.data[_LOVELACE_REGISTER_KEY] = version
            return

        async def _retry_later(_now: Any) -> None:
            await async_register_lovelace_cards(hass, _retry=_retry + 1)

        async_call_later(hass, 5, _retry_later)
        return

    if not _can_register_storage_resources(lovelace):
        hass.data[_LOVELACE_REGISTER_KEY] = version
        return

    resources = lovelace.resources
    try:
        await _async_ensure_resources_loaded(resources)
        await _async_upsert_flow_scene_resource(hass, lovelace, url, version)
    except Exception:
        if _retry >= _MAX_LOVELACE_RETRIES:
            _LOGGER.exception(
                "Fox Flow Scene Lovelace storage resource failed after %s attempts; "
                "frontend module URL %s is still active",
                _MAX_LOVELACE_RETRIES,
                url,
            )
            hass.data[_LOVELACE_REGISTER_KEY] = version
            return
        _LOGGER.debug("Fox Flow Scene storage registration retry %s", _retry + 1, exc_info=True)

        async def _retry_after_error(_now: Any) -> None:
            await async_register_lovelace_cards(hass, _retry=_retry + 1)

        async_call_later(hass, 5, _retry_after_error)


async def _async_upsert_flow_scene_resource(
    hass: HomeAssistant,
    lovelace: Any,
    url: str,
    version: str,
) -> None:
    path = _resource_path(url)
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
