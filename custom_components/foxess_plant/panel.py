"""Register the Fox Plant sidebar panel."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_ICON, PANEL_STATIC_URL, PANEL_TITLE, PANEL_URL_PATH

_LOGGER = logging.getLogger(__name__)

PANEL_COMPONENT = "foxess-plant-panel"
WWW_DIR = Path(__path__).parent / "www"


def _panel_exists(hass: HomeAssistant) -> bool:
    """Return True if our panel URL is already registered."""
    from homeassistant.components import frontend

    if hasattr(frontend, "async_panel_exists"):
        return frontend.async_panel_exists(hass, PANEL_URL_PATH)
    panels = hass.data.get("frontend_panels", {})
    return PANEL_URL_PATH in panels


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
    from homeassistant.components import frontend, panel_custom
    from homeassistant.components.http import StaticPathConfig

    if not WWW_DIR.is_dir() or not (WWW_DIR / "foxess-plant-panel.js").is_file():
        _LOGGER.warning("Fox Plant panel assets missing at %s", WWW_DIR)
        return

    config = build_panel_config(hass)

    if _panel_exists(hass):
        frontend.async_register_built_in_panel(
            hass,
            component_name=PANEL_COMPONENT,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL_PATH,
            config=config,
            require_admin=False,
            update=True,
        )
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_STATIC_URL,
                str(WWW_DIR),
                False,
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
        config=config,
    )
    _LOGGER.info("Fox Plant panel registered at /%s", PANEL_URL_PATH)


async def async_update_panel(hass: HomeAssistant) -> None:
    """Refresh panel config when plant entries change."""
    if not _panel_exists(hass):
        return
    from homeassistant.components import frontend

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
