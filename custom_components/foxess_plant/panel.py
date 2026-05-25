"""Register the Fox Plant sidebar panel."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_ICON, PANEL_STATIC_URL, PANEL_TITLE, PANEL_URL_PATH

_LOGGER = logging.getLogger(__name__)

PANEL_COMPONENT = "foxess-plant-panel"
WWW_DIR = Path(__path__).parent / "www"


def build_panel_config(hass: HomeAssistant) -> dict[str, Any]:
    """Build panel config payload passed to the frontend web component."""
    plants: list[dict[str, Any]] = []
    for entry_id, data in hass.data.get(DOMAIN, {}).items():
        coordinator = data.get("coordinator")
        if coordinator is None:
            continue
        plant = coordinator.plant
        plants.append(
            {
                "entry_id": entry_id,
                "title": coordinator.config_entry.title,
                "inverter": plant.inverter_target,
                "entity_map": plant.entity_map,
            }
        )
    return {"plants": plants}


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the Fox Plant panel in the HA sidebar."""
    if frontend.async_panel_exists(hass, PANEL_URL_PATH):
        frontend.async_register_built_in_panel(
            hass,
            component_name=PANEL_COMPONENT,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL_PATH,
            config=build_panel_config(hass),
            require_admin=False,
            update=True,
        )
        return

    if not WWW_DIR.is_dir():
        _LOGGER.warning("Fox Plant panel assets missing at %s", WWW_DIR)
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_STATIC_URL,
                str(WWW_DIR),
                cache_headers=False,
            )
        ]
    )

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT,
        frontend_url_path=PANEL_URL_PATH,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{PANEL_STATIC_URL}/foxess-plant-panel.js",
        embed_iframe=False,
        require_admin=False,
        config=build_panel_config(hass),
    )
    _LOGGER.info("Fox Plant panel registered at /%s", PANEL_URL_PATH)


async def async_update_panel(hass: HomeAssistant) -> None:
    """Refresh panel config when plant entries change."""
    if not frontend.async_panel_exists(hass, PANEL_URL_PATH):
        return
    frontend.async_register_built_in_panel(
        hass,
        component_name=PANEL_COMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config=build_panel_config(hass),
        require_admin=False,
        update=True,
    )
