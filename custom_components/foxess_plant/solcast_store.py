"""Persist Solcast PV forecasts (parsed + raw API) across restarts and for history."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, SOLCAST_FORECAST_HISTORY_MAX

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


def _storage_key(entry_id: str) -> str:
    return f"{DOMAIN}.solcast_forecasts.{entry_id}"


def cache_from_storage(data: dict[str, Any] | None) -> dict[str, Any]:
    """Rebuild coordinator in-memory cache from stored document."""
    if not data:
        return {}
    current = data.get("current")
    if not isinstance(current, dict):
        return {}
    cache = deepcopy(current)
    if cache.get("updated_at") and not cache.get("pv_forecast_fetched_at"):
        cache["pv_forecast_fetched_at"] = cache["updated_at"]
    return cache


class SolcastForecastStore:
    """JSON store under HA config/.storage for current forecast + poll history."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, _storage_key(entry_id))

    async def async_load(self) -> dict[str, Any]:
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return {"version": STORAGE_VERSION, "current": None, "history": []}
        data.setdefault("history", [])
        return data

    async def async_record_poll(self, cache: dict[str, Any]) -> int:
        """Save latest poll as current and append to bounded history. Returns history length."""
        if not cache.get("pv_forecast_parsed"):
            return SolcastForecastStore.history_count(await self.async_load())
        snapshot = deepcopy(cache)
        fetched_at = snapshot.get("updated_at") or snapshot.get("pv_forecast_fetched_at")
        data = await self.async_load()
        data["current"] = snapshot
        history: list[dict[str, Any]] = list(data.get("history") or [])
        history.append(
            {
                "fetched_at": fetched_at,
                "cache": snapshot,
            }
        )
        if len(history) > SOLCAST_FORECAST_HISTORY_MAX:
            history = history[-SOLCAST_FORECAST_HISTORY_MAX:]
        data["history"] = history
        await self._store.async_save(data)
        _LOGGER.debug(
            "Solcast forecast stored (periods=%s, history=%s)",
            (snapshot.get("pv_forecast_parsed") or {}).get("period_count"),
            len(history),
        )
        return len(history)

    @staticmethod
    def history_count(data: dict[str, Any] | None) -> int:
        if not data:
            return 0
        history = data.get("history")
        return len(history) if isinstance(history, list) else 0
