"""Auto-link Google Weather as the native StormSafe weather source."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import CONF_STORM_PREP, DEFAULT_STORM_PREP, STORM_ALERT_PROVIDER_GOOGLE
from .panel_config import discover_google_weather, resolve_google_weather_entry
from .storm_forecast import DEFAULT_FORECAST_LEAD_HOURS


def apply_google_weather_storm_defaults(hass: HomeAssistant, entry_data: dict[str, Any]) -> dict[str, Any]:
    """Wire storm_prep to Google Weather when a single location is configured."""
    gw = discover_google_weather(hass)
    entries = gw.get("entries") or []
    if len(entries) != 1:
        return entry_data

    entry = entries[0]
    sources = resolve_google_weather_entry(hass, entry["entry_id"])
    storm = dict(entry_data.get(CONF_STORM_PREP) or DEFAULT_STORM_PREP)
    storm.update(
        {
            "alert_provider": STORM_ALERT_PROVIDER_GOOGLE,
            "google_weather_entry_id": entry["entry_id"],
            "use_weather_condition": bool(sources.get("condition_entity_id")),
            "use_forecast_lead": bool(sources.get("weather_entity_id")),
            "forecast_lead_hours": DEFAULT_FORECAST_LEAD_HOURS,
            "condition_entity_id": sources.get("condition_entity_id"),
            "weather_entity_id": sources.get("weather_entity_id"),
            "trigger_entities": sources.get("alert_trigger_ids") or [],
        }
    )
    entry_data = dict(entry_data)
    entry_data[CONF_STORM_PREP] = storm
    return entry_data


def google_weather_install_status(hass: HomeAssistant) -> dict[str, Any]:
    """Summary for config flow / panel install wizard."""
    gw = discover_google_weather(hass)
    entries = gw.get("entries") or []
    return {
        "installed": gw.get("installed", False),
        "entry_count": len(entries),
        "auto_link_ready": len(entries) == 1,
        "hacs_repo": gw.get("hacs_repo"),
        "setup_status": gw.get("setup_status"),
    }
