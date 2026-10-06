"""Remove Fox Plant entities nothing provides any more (they sit in HA as "Unavailable").

Only two exact cases, never anything the current install still creates:
- entities of a Fox Plant config entry that no longer exists (HA left 15 behind after an install was re-added);
- entities of this install whose unique_id suffix is listed in RETIRED_UNIQUE_SUFFIXES (renamed or dropped).
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# unique_id = f"{entry_id}_{suffix}"; add a suffix here when an entity is renamed or dropped
RETIRED_UNIQUE_SUFFIXES: frozenset[str] = frozenset(
    {
        "solcast_pv_forecast_remaining",  # now "Forecast remaining today" (solcast_forecast_remaining_today)
        "solcast_pv_power_now",  # now "Power now" (solcast_power_now)
    }
)


def stale_entity_ids(
    registry_entries: list[er.RegistryEntry], current_entry_id: str, live_entry_ids: set[str]
) -> list[str]:
    """Entity ids to remove from the registry."""
    retired = {f"{current_entry_id}_{suffix}" for suffix in RETIRED_UNIQUE_SUFFIXES}
    out: list[str] = []
    for entry in registry_entries:
        if entry.platform != DOMAIN:
            continue
        if entry.config_entry_id not in live_entry_ids or (
            entry.config_entry_id == current_entry_id and entry.unique_id in retired
        ):
            out.append(entry.entity_id)
    return sorted(out)


def async_remove_stale_entities(hass: HomeAssistant, entry: ConfigEntry) -> list[str]:
    registry = er.async_get(hass)
    live = {e.entry_id for e in hass.config_entries.async_entries(DOMAIN)}
    removed = stale_entity_ids(list(registry.entities.values()), entry.entry_id, live)
    for entity_id in removed:
        registry.async_remove(entity_id)
    if removed:
        _LOGGER.info("Removed %d Fox Plant entities nothing provides any more: %s", len(removed), ", ".join(removed))
    return removed
