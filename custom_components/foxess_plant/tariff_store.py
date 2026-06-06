"""Persist tariff rate snapshots for future dynamic/API tariffs and cost analysis."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
TARIFF_RATE_HISTORY_MAX = 2880  # ~30 days at 15 min if polled from API later


def _storage_key(entry_id: str) -> str:
    return f"foxess_plant.tariff_rates.{entry_id}"


class TariffRateStore:
    """JSON store for current tariff rates + bounded history (recorder-friendly snapshots)."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, _storage_key(entry_id))

    async def async_load(self) -> dict[str, Any]:
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return {"version": STORAGE_VERSION, "current": None, "history": []}
        data.setdefault("history", [])
        return data

    async def async_record_rates(
        self,
        *,
        rates: dict[str, Any],
        source: str = "static",
        recorded_at: str | None = None,
    ) -> int:
        """Save latest rates and append to bounded history. Returns history length."""
        snapshot = {
            "recorded_at": recorded_at,
            "source": source,
            "rates": deepcopy(rates),
        }
        data = await self.async_load()
        data["current"] = snapshot
        history: list[dict[str, Any]] = list(data.get("history") or [])
        if not history or history[-1].get("rates") != snapshot["rates"]:
            history.append(snapshot)
        if len(history) > TARIFF_RATE_HISTORY_MAX:
            history = history[-TARIFF_RATE_HISTORY_MAX:]
        data["history"] = history
        await self._store.async_save(data)
        _LOGGER.debug("Tariff rates stored (source=%s, history=%s)", source, len(history))
        return len(history)

    @staticmethod
    def history_count(data: dict[str, Any] | None) -> int:
        if not data:
            return 0
        history = data.get("history")
        return len(history) if isinstance(history, list) else 0
