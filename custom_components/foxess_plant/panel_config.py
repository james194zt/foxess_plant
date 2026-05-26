"""Panel-facing config helpers (trigger discovery, storm prep save)."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, State

# Entity id / friendly-name hints for weather & warning sensors.
_TRIGGER_HINTS = (
    "weather",
    "warning",
    "warn",
    "storm",
    "metoffice",
    "met_office",
    "met office",
    "openweathermap",
    "accuweather",
    "bureau",
    "bom",
    "amber",
    "severe",
    "hail",
    "wind",
    "flood",
    "thunder",
    "lightning",
    "nws",
    "yr.no",
    "forecast",
)

_WARNING_DEVICE_CLASSES = frozenset(
    {
        "safety",
        "problem",
        "opening",
    }
)


def _friendly_name(state: State) -> str:
    name = state.attributes.get("friendly_name")
    return str(name) if name else state.entity_id


def _is_trigger_candidate(state: State) -> bool:
    domain = state.entity_id.split(".", 1)[0]
    if domain in ("binary_sensor", "input_boolean"):
        return True
    if domain == "sensor" and _is_suggested_trigger(state):
        return True
    return False


def _is_suggested_trigger(state: State) -> bool:
    blob = f"{state.entity_id} {_friendly_name(state)}".lower()
    if any(hint in blob for hint in _TRIGGER_HINTS):
        return True
    device_class = state.attributes.get("device_class")
    return device_class in _WARNING_DEVICE_CLASSES


def list_trigger_candidates(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Binary sensors / input_booleans for StormSafe trigger pickers."""
    entities: list[dict[str, Any]] = []
    for state in hass.states.async_all():
        if not _is_trigger_candidate(state):
            continue
        entities.append(
            {
                "entity_id": state.entity_id,
                "name": _friendly_name(state),
                "state": state.state,
                "suggested": _is_suggested_trigger(state),
            }
        )
    entities.sort(key=lambda row: (not row["suggested"], row["name"].lower()))
    return entities
