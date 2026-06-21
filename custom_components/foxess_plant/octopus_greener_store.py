"""Persist Octopus Greener Nights and carbon intensity snapshots."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
GREENER_HISTORY_MAX = 120  # ~4 months of daily snapshots


def _storage_key(entry_id: str) -> str:
    return f"foxess_plant.octopus_greener.{entry_id}"


class OctopusGreenerStore:
    """JSON store for greener nights + carbon intensity history."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, _storage_key(entry_id))

    async def async_load(self) -> dict[str, Any]:
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return {
                "version": STORAGE_VERSION,
                "current": None,
                "history": [],
            }
        data.setdefault("history", [])
        return data

    async def async_record_snapshot(
        self,
        *,
        snapshot: dict[str, Any],
        recorded_at: str,
    ) -> int:
        """Save latest snapshot and append to bounded history."""
        entry = {
            "recorded_at": recorded_at,
            "snapshot": deepcopy(snapshot),
        }
        data = await self.async_load()
        data["current"] = entry
        history: list[dict[str, Any]] = list(data.get("history") or [])
        prev = history[-1] if history else None
        prev_snap = (prev or {}).get("snapshot") if isinstance(prev, dict) else None
        if prev_snap != entry["snapshot"]:
            history.append(entry)
        if len(history) > GREENER_HISTORY_MAX:
            history = history[-GREENER_HISTORY_MAX:]
        data["history"] = history
        await self._store.async_save(data)
        _LOGGER.debug("Octopus greener snapshot stored (history=%s)", len(history))
        return len(history)

    @staticmethod
    def history_count(data: dict[str, Any] | None) -> int:
        if not data:
            return 0
        history = data.get("history")
        return len(history) if isinstance(history, list) else 0
