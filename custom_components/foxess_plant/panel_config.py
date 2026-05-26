"""Panel-facing config helpers (trigger discovery, storm prep save)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

from .const import (
    GOOGLE_WEATHER_ALERT_SUFFIXES,
    GOOGLE_WEATHER_DOMAIN,
    STORM_ALERT_PROVIDER_GOOGLE,
)
from .storm_weather import read_condition_snapshot, storm_type_catalog

_OTHER_TRIGGER_HINTS = (
    "warning",
    "warn",
    "alert",
    "meteoalarm",
    "nws",
    "weather_alert",
    "severe",
)

_WARNING_DEVICE_CLASSES = frozenset({"safety", "problem"})

# Shown in the panel as linked forecast data (not used as on/off triggers yet).
_GOOGLE_FORECAST_SENSOR_SUFFIXES = (
    "_thunderstorm_probability",
    "_precipitation_probability",
    "_weather_condition",
)


def _friendly_name(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    if state:
        name = state.attributes.get("friendly_name")
        if name:
            return str(name)
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry and entry.original_name:
        return str(entry.original_name)
    return entity_id


def _integration_domain(hass: HomeAssistant, entity_id: str) -> str | None:
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if not entry or not entry.config_entry_id:
        return None
    cfg = hass.config_entries.async_get_entry(entry.config_entry_id)
    return cfg.domain if cfg else None


def _entities_for_config_entry(hass: HomeAssistant, entry_id: str) -> list[str]:
    registry = er.async_get(hass)
    return [
        entity_id
        for entity_id, ent in registry.entities.items()
        if ent.config_entry_id == entry_id
    ]


def _is_google_weather_alert_entity(hass: HomeAssistant, entity_id: str) -> bool:
    if not entity_id.startswith("binary_sensor."):
        return False
    if _integration_domain(hass, entity_id) != GOOGLE_WEATHER_DOMAIN:
        return False
    object_id = entity_id.split(".", 1)[1]
    return any(object_id.endswith(suffix) for suffix in GOOGLE_WEATHER_ALERT_SUFFIXES)


def _google_alert_role(entity_id: str) -> str:
    object_id = entity_id.split(".", 1)[1]
    if object_id.endswith("_urgent_weather_alert"):
        return "urgent"
    if object_id.endswith("_severe_weather_alert"):
        return "severe"
    return "any"


def _alert_row(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    state = hass.states.get(entity_id)
    return {
        "entity_id": entity_id,
        "name": _friendly_name(hass, entity_id),
        "state": state.state if state else "unavailable",
        "role": _google_alert_role(entity_id),
    }


def _find_weather_condition_entity(hass: HomeAssistant, entry_id: str) -> str | None:
    for entity_id in _entities_for_config_entry(hass, entry_id):
        if entity_id.startswith("sensor.") and entity_id.endswith("_weather_condition"):
            return entity_id
    return None


def _build_google_weather_entry(hass: HomeAssistant, cfg: ConfigEntry) -> dict[str, Any]:
    entry_id = cfg.entry_id
    title = cfg.title or "Google Weather"
    weather_entity: str | None = None
    condition_entity: str | None = None
    alert_entities: list[dict[str, Any]] = []
    forecast_entities: list[str] = []
    has_daytime = False

    for entity_id in _entities_for_config_entry(hass, entry_id):
        if entity_id.startswith("weather."):
            weather_entity = entity_id
            continue
        if entity_id.startswith("binary_sensor."):
            if entity_id.endswith("_is_daytime"):
                has_daytime = True
                continue
            if _is_google_weather_alert_entity(hass, entity_id):
                alert_entities.append(_alert_row(hass, entity_id))
            continue
        if entity_id.startswith("sensor."):
            if entity_id.endswith("_weather_condition"):
                condition_entity = entity_id
                continue
            object_id = entity_id.split(".", 1)[1]
            if any(object_id.endswith(suffix) for suffix in _GOOGLE_FORECAST_SENSOR_SUFFIXES):
                forecast_entities.append(entity_id)

    alert_entities.sort(key=lambda row: (row["role"] != "any", row["name"].lower()))
    alert_trigger_ids = [row["entity_id"] for row in alert_entities]
    current_condition = read_condition_snapshot(hass, condition_entity, weather_entity)

    if alert_trigger_ids:
        setup_status = "ready"
    elif condition_entity:
        setup_status = "condition_ready"
    elif weather_entity or has_daytime or forecast_entities:
        setup_status = "no_condition_sensor"
    else:
        setup_status = "not_configured"

    return {
        "entry_id": entry_id,
        "title": title,
        "weather_entity": weather_entity,
        "condition_entity_id": condition_entity,
        "current_condition": current_condition,
        "alert_entities": alert_entities,
        "alert_trigger_ids": alert_trigger_ids,
        "alerts_supported": bool(alert_trigger_ids),
        "condition_supported": bool(condition_entity),
        "setup_status": setup_status,
        "forecast_entities": sorted(forecast_entities),
        "has_daytime_sensor": has_daytime,
    }


def resolve_google_weather_entry(hass: HomeAssistant, entry_id: str | None) -> dict[str, Any]:
    """Entities StormSafe uses for one Google Weather config entry."""
    if not entry_id:
        return {
            "alert_trigger_ids": [],
            "condition_entity_id": None,
            "weather_entity_id": None,
        }
    cfg = hass.config_entries.async_get_entry(entry_id)
    if not cfg or cfg.domain != GOOGLE_WEATHER_DOMAIN:
        return {
            "alert_trigger_ids": [],
            "condition_entity_id": None,
            "weather_entity_id": None,
        }
    weather_entity: str | None = None
    condition_entity = _find_weather_condition_entity(hass, entry_id)
    alert_ids = [
        entity_id
        for entity_id in _entities_for_config_entry(hass, entry_id)
        if _is_google_weather_alert_entity(hass, entity_id)
    ]
    for entity_id in _entities_for_config_entry(hass, entry_id):
        if entity_id.startswith("weather."):
            weather_entity = entity_id
            break
    return {
        "alert_trigger_ids": alert_ids,
        "condition_entity_id": condition_entity,
        "weather_entity_id": weather_entity,
    }


def resolve_google_weather_triggers(hass: HomeAssistant, entry_id: str | None) -> list[str]:
    """Alert binary sensors for one Google Weather config entry."""
    return resolve_google_weather_entry(hass, entry_id)["alert_trigger_ids"]


def infer_google_weather_entry_id(
    entries: list[dict[str, Any]],
    trigger_entities: list[str],
    *,
    condition_entity_id: str | None = None,
    weather_entity_id: str | None = None,
) -> str | None:
    """Pick the Google Weather entry that best matches saved storm config."""
    if not entries:
        return None
    if condition_entity_id:
        for entry in entries:
            if entry.get("condition_entity_id") == condition_entity_id:
                return entry["entry_id"]
    if weather_entity_id:
        for entry in entries:
            if entry.get("weather_entity") == weather_entity_id:
                return entry["entry_id"]
    triggers = set(trigger_entities)
    if triggers:
        for entry in entries:
            alert_ids = set(entry.get("alert_trigger_ids") or [])
            if triggers <= alert_ids and alert_ids:
                return entry["entry_id"]
    if len(entries) == 1:
        return entries[0]["entry_id"]
    return None


def discover_google_weather(hass: HomeAssistant) -> dict[str, Any]:
    """Google Weather config entries and alert status for StormSafe."""
    configs = hass.config_entries.async_entries(GOOGLE_WEATHER_DOMAIN)
    entries = [_build_google_weather_entry(hass, cfg) for cfg in configs]
    entries.sort(key=lambda row: row["title"].lower())

    all_alert_ids: list[str] = []
    for entry in entries:
        all_alert_ids.extend(entry["alert_trigger_ids"])

    if any(entry["alerts_supported"] for entry in entries):
        setup_status = "ready"
    elif any(entry.get("condition_supported") for entry in entries):
        setup_status = "condition_ready"
    elif not configs:
        setup_status = "not_installed"
    elif entries:
        setup_status = "no_condition_sensor"
    else:
        setup_status = "not_configured"

    return {
        "installed": bool(configs),
        "entries": entries,
        "alerts_supported": bool(all_alert_ids),
        "condition_supported": any(entry.get("condition_supported") for entry in entries),
        "storm_condition_types": storm_type_catalog(),
        "setup_status": setup_status,
        "alert_entities": [
            row for entry in entries for row in entry["alert_entities"]
        ],
        "weather_entities": [
            e["weather_entity"] for e in entries if e.get("weather_entity")
        ],
        "recommended_trigger_ids": all_alert_ids,
        "hacs_repo": "https://github.com/safepay/ha_google_weather",
    }


def _is_trigger_candidate(hass: HomeAssistant, state: State) -> bool:
    if _is_google_weather_alert_entity(hass, state.entity_id):
        return True
    domain = state.entity_id.split(".", 1)[0]
    if domain in ("binary_sensor", "input_boolean"):
        return True
    if domain == "sensor":
        blob = f"{state.entity_id} {state.attributes.get('friendly_name', '')}".lower()
        return any(hint in blob for hint in _OTHER_TRIGGER_HINTS)
    return False


def _is_suggested_other(hass: HomeAssistant, state: State) -> bool:
    if _is_google_weather_alert_entity(hass, state.entity_id):
        return False
    blob = f"{state.entity_id} {state.attributes.get('friendly_name', '')}".lower()
    if any(hint in blob for hint in _OTHER_TRIGGER_HINTS):
        return True
    device_class = state.attributes.get("device_class")
    return device_class in _WARNING_DEVICE_CLASSES


def list_trigger_candidates(hass: HomeAssistant) -> dict[str, Any]:
    """StormSafe setup metadata; entity list is only for advanced manual picking."""
    google = discover_google_weather(hass)
    google_ids = set(google["recommended_trigger_ids"])

    entities: list[dict[str, Any]] = []
    for state in hass.states.async_all():
        if not _is_trigger_candidate(hass, state):
            continue
        is_gw = state.entity_id in google_ids
        name = state.attributes.get("friendly_name")
        entities.append(
            {
                "entity_id": state.entity_id,
                "name": str(name) if name else state.entity_id,
                "state": state.state,
                "suggested": is_gw or _is_suggested_other(hass, state),
                "provider": STORM_ALERT_PROVIDER_GOOGLE if is_gw else None,
                "role": _google_alert_role(state.entity_id) if is_gw else None,
            }
        )

    entities.sort(
        key=lambda row: (
            row["provider"] != STORM_ALERT_PROVIDER_GOOGLE,
            not row["suggested"],
            row["name"].lower(),
        )
    )

    return {
        "entities": entities,
        "google_weather": google,
        "default_provider": STORM_ALERT_PROVIDER_GOOGLE,
        "recommended_triggers": google["recommended_trigger_ids"],
    }
