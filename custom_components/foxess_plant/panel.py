"""Register the Fox Plant sidebar panel."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_ICON, PANEL_STATIC_URL, PANEL_TITLE, PANEL_URL_PATH

_LOGGER = logging.getLogger(__name__)

PANEL_COMPONENT = "foxess-plant-panel"
WWW_DIR = Path(__file__).parent / "www"
_STATIC_DATA_KEY = "_foxess_plant_static_registered"


def _panel_exists(hass: HomeAssistant) -> bool:
    """Return True if our panel URL is already registered."""
    from homeassistant.components import frontend

    if hasattr(frontend, "async_panel_exists"):
        return frontend.async_panel_exists(hass, PANEL_URL_PATH)
    panels = hass.data.get("frontend_panels", {})
    return PANEL_URL_PATH in panels


def build_panel_config(hass: HomeAssistant) -> dict[str, Any]:
    """Build plant list passed to the frontend web component."""
    plants: list[dict[str, Any]] = []
    for entry_id, data in hass.data.get(DOMAIN, {}).items():
        if not isinstance(data, dict):
            continue
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


def _build_frontend_panel_config(hass: HomeAssistant) -> dict[str, Any]:
    """Wrap plant config in the structure HA custom panels expect."""
    return {
        **build_panel_config(hass),
        "_panel_custom": {
            "name": PANEL_COMPONENT,
            "embed_iframe": False,
            "trust_external": False,
            "module_url": f"{PANEL_STATIC_URL}/foxess-plant-panel.js",
        },
    }


async def _async_ensure_static_paths(hass: HomeAssistant) -> bool:
    """Register www assets (must run on every HA start)."""
    if hass.data.get(_STATIC_DATA_KEY):
        return True

    if not WWW_DIR.is_dir() or not (WWW_DIR / "foxess-plant-panel.js").is_file():
        _LOGGER.warning("Fox Plant panel assets missing at %s", WWW_DIR)
        return False

    from homeassistant.components.http import StaticPathConfig

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_STATIC_URL,
                str(WWW_DIR),
                False,
            )
        ]
    )
    hass.data[_STATIC_DATA_KEY] = True
    return True


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register or update the Fox Plant panel in the HA sidebar."""
    from homeassistant.components import frontend

    if not await _async_ensure_static_paths(hass):
        return

    config = _build_frontend_panel_config(hass)
    update = _panel_exists(hass)

    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config=config,
        require_admin=False,
        update=update,
    )
    _LOGGER.info(
        "Fox Plant panel %s at /%s",
        "updated" if update else "registered",
        PANEL_URL_PATH,
    )


async def async_update_panel(hass: HomeAssistant) -> None:
    """Refresh panel config when plant entries change."""
    if not _panel_exists(hass):
        return
    await async_register_panel(hass)
