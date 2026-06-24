"""Register FoxESS Plant Lovelace card resources (storage-mode dashboards)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import Event, HomeAssistant
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


def _register_frontend_module(hass: HomeAssistant, url: str) -> None:
    """Load card JS globally (works before Lovelace resources finish loading)."""
    from homeassistant.components.frontend import add_extra_js_url

    add_extra_js_url(hass, url)


def _get_storage_resources(hass: HomeAssistant) -> Any | None:
    """Return Lovelace storage resources collection (None for YAML resource_mode)."""
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        return None

    resources = getattr(lovelace, "resources", None)
    if resources is None:
        return None

    store = getattr(resources, "store", None)
    if store is None:
        _LOGGER.debug(
            "Lovelace YAML resource_mode: Fox Flow Scene uses frontend module URL only"
        )
        return None

    if getattr(store, "key", None) != "lovelace_resources":
        return None
    if getattr(store, "version", None) != 1:
        return None

    return resources


async def async_register_lovelace_cards(hass: HomeAssistant, *, _retry: int = 0) -> None:
    """Add or update the Fox Flow Scene card module in Lovelace resources."""
    version = _integration_version()
    url = flow_scene_card_resource_url()

    _register_frontend_module(hass, url)

    if hass.data.get(_LOVELACE_REGISTER_KEY) == version:
        return

    resources = _get_storage_resources(hass)
    if resources is None:
        if _retry < _MAX_LOVELACE_RETRIES and hass.data.get("lovelace") is None:

            async def _retry_later(_now: Any) -> None:
                await async_register_lovelace_cards(hass, _retry=_retry + 1)

            async_call_later(hass, 5, _retry_later)
            return

        hass.data[_LOVELACE_REGISTER_KEY] = version
        _LOGGER.info(
            "Fox Flow Scene card registered as frontend module %s — "
            "hard-refresh the browser, then Add card → By card → search Fox Flow Scene",
            url,
        )
        return

    try:
        if not getattr(resources, "loaded", False):
            await resources.async_load()
        await _async_upsert_flow_scene_resource(hass, resources, url, version)
        hass.data[_LOVELACE_REGISTER_KEY] = version
        _LOGGER.info(
            "Fox Flow Scene Lovelace card v%s registered — "
            "hard-refresh the browser, then Add card → By card → search Fox Flow Scene",
            version,
        )
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
    resources: Any,
    url: str,
    version: str,
) -> None:
    path = _resource_path(url)
    existing = [
        item
        for item in resources.async_items()
        if _resource_path(item.get("url", "")) == path
    ]
    payload = {"res_type": "module", "url": url}
    if existing:
        current = existing[0]
        if _resource_version(current.get("url", "")) != version:
            _LOGGER.info("Updating Fox Flow Scene Lovelace card to v%s", version)
            await resources.async_update_item(current["id"], payload)
    else:
        _LOGGER.info("Registering Fox Flow Scene Lovelace card v%s", version)
        await resources.async_create_item(payload)


def async_listen_lovelace_loaded(hass: HomeAssistant) -> None:
    """Register the card when the lovelace component becomes available."""

    async def _on_component_loaded(event: Event) -> None:
        if event.data.get("component") != "lovelace":
            return
        try:
            await async_register_lovelace_cards(hass)
        except Exception:
            _LOGGER.exception("Fox Flow Scene Lovelace card registration failed on lovelace load")

    hass.bus.async_listen(EVENT_COMPONENT_LOADED, _on_component_loaded)
