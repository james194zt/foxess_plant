"""Register the Fox Plant sidebar panel."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    MODBUS_DOMAIN,
    PANEL_BRAND_ICON_STATIC,
    PANEL_ICON,
    PANEL_STATIC_URL,
    PANEL_TITLE,
    PANEL_URL_PATH,
)

_LOGGER = logging.getLogger(__name__)

PANEL_COMPONENT = "foxess-plant-panel"
PANEL_JS_FILE = "foxess-plant-panel.js"
WWW_DIR = Path(__file__).parent / "www"
_STATIC_DATA_KEY = "_foxess_plant_static_registered"
PANEL_FLOW_PATHS_VER = "flow-comet-v3"
_PANEL_JS_MISSING_LOGGED = False


def panel_js_path() -> Path:
    return WWW_DIR / PANEL_JS_FILE


def panel_js_available() -> bool:
    return panel_js_path().is_file()


def _log_panel_js_missing_once() -> None:
    global _PANEL_JS_MISSING_LOGGED
    if _PANEL_JS_MISSING_LOGGED:
        return
    _PANEL_JS_MISSING_LOGGED = True
    _LOGGER.error(
        "Fox Plant panel JS missing at %s — copy the full custom_components/foxess_plant "
        "folder from the release (including www/%s), then restart Home Assistant",
        panel_js_path(),
        PANEL_JS_FILE,
    )


def _panel_component_name() -> str:
    """Versioned custom element tag so HA loads new panel code instead of a cached class."""
    return f"{PANEL_COMPONENT}-{_panel_js_version().replace('.', '_')}"


def _panel_js_version() -> str:
    """Read manifest at call time so integration reload picks up HACS updates."""
    with (Path(__file__).parent / "manifest.json").open(encoding="utf-8") as mf:
        return json.load(mf).get("version", "0")


def _panel_js_fingerprint() -> str:
    """Short hash of panel JS so module_url changes whenever the file changes."""
    path = panel_js_path()
    if not path.is_file():
        _log_panel_js_missing_once()
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _panel_js_cache_name() -> str:
    """Versioned filename so browsers cannot reuse a stale ES module cache."""
    ver = _panel_js_version().replace(".", "_")
    return f"foxess-plant-panel.v{ver}.{_panel_js_fingerprint()}.js"


def _sync_versioned_panel_js() -> None:
    """Copy canonical panel JS to a unique filename whenever content changes."""
    src = panel_js_path()
    if not src.is_file():
        return
    dest = WWW_DIR / _panel_js_cache_name()
    data = src.read_bytes()
    if not dest.is_file() or dest.read_bytes() != data:
        dest.write_bytes(data)
    for old in WWW_DIR.glob("foxess-plant-panel.v*.js"):
        if old.name != dest.name:
            try:
                old.unlink()
            except OSError:
                pass


def _panel_js_module_url() -> str:
    return f"{PANEL_STATIC_URL}/{_panel_js_cache_name()}"


def _panel_js_build() -> str:
    return f"{_panel_js_version()}-{_panel_js_fingerprint()}"


def _compute_panel_disk_info() -> dict[str, str]:
    """Manifest + JS build read from disk (for stale-panel detection in the UI)."""
    info: dict[str, str] = {
        "manifest_version": _panel_js_version(),
        "js_build": _panel_js_build(),
        "module_url": _panel_js_module_url() if panel_js_available() else "",
        "element": _panel_component_name(),
    }
    if not panel_js_available():
        info["panel_assets_missing"] = "true"
        info["panel_assets_path"] = str(panel_js_path())
    return info


def get_panel_disk_info(hass: HomeAssistant | None = None) -> dict[str, str]:
    """Return cached panel build info when available (avoids disk I/O on websocket polls)."""
    if hass is not None:
        cached = hass.data.get(_PANEL_DISK_INFO_KEY)
        if isinstance(cached, dict):
            return dict(cached)
    return _compute_panel_disk_info()


def _prepare_panel_assets() -> dict[str, str]:
    """Sync disk work for panel registration (run in executor)."""
    _sync_versioned_panel_js()
    return _compute_panel_disk_info()


_PANEL_DISK_INFO_KEY = "_foxess_plant_panel_disk_info"
_REGISTERED_BUILD_KEY = "_foxess_plant_panel_registered_build"


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
    return {
        "plants": plants,
        "brand_domain": DOMAIN,
        "modbus_brand_domain": MODBUS_DOMAIN,
        "brand_icon_static": PANEL_BRAND_ICON_STATIC,
        "panel_js_build": _panel_js_build(),
        "panel_js_module_url": _panel_js_module_url(),
        "flow_paths_ver": PANEL_FLOW_PATHS_VER,
        "panel_element": _panel_component_name(),
    }


def _build_frontend_panel_config(hass: HomeAssistant) -> dict[str, Any]:
    """Wrap plant config in the structure HA custom panels expect."""
    return {
        **build_panel_config(hass),
        "_panel_custom": {
            "name": _panel_component_name(),
            "embed_iframe": False,
            "trust_external": False,
            "module_url": _panel_js_module_url(),
        },
    }


async def _async_ensure_static_paths(hass: HomeAssistant) -> bool:
    """Register www assets (must run on every HA start)."""
    if hass.data.get(_STATIC_DATA_KEY):
        return True

    if not WWW_DIR.is_dir() or not panel_js_available():
        _log_panel_js_missing_once()
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

    hass.data[_PANEL_DISK_INFO_KEY] = await hass.async_add_executor_job(_prepare_panel_assets)

    config = _build_frontend_panel_config(hass)
    build = config.get("panel_js_build", "?")
    existed = _panel_exists(hass)
    if existed:
        # Force HA to pick up a new module_url after HACS updates (update=True is not enough).
        frontend.async_remove_panel(hass, PANEL_URL_PATH)

    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        config=config,
        require_admin=False,
        update=False,
        config_panel_domain=DOMAIN,
    )
    _LOGGER.info(
        "Fox Plant panel %s at /%s (element=%s js build=%s url=%s) — "
        "if the browser still shows an old build, restart HA or call foxess_plant.reload_panel",
        "re-registered" if existed else "registered",
        PANEL_URL_PATH,
        _panel_component_name(),
        build,
        _panel_js_module_url(),
    )
    hass.data[_REGISTERED_BUILD_KEY] = build


async def async_update_panel(hass: HomeAssistant) -> None:
    """Refresh panel config when plant entries change."""
    if not _panel_exists(hass):
        return
    await async_register_panel(hass)
