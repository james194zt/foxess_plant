"""Persist the last good E.ON Next tariff fetch across restarts.

E.ON's fixed and time-of-use tariffs don't change until the agreement ends, and its
sign-in depends on a browser token that can lapse. The last good response keeps
SmartCharge and the tariff sensors right through sign-in outages and restarts, instead
of dropping to "no rates" until E.ON answers again. Octopus is deliberately not stored.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1


class SupplierTariffStore:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"foxess_plant.supplier_tariff.{entry_id}")

    async def async_load(self, provider: str) -> dict[str, Any] | None:
        data: Any = await self._store.async_load()
        if not isinstance(data, dict) or data.get("provider") != provider:
            return None
        cache = data.get("cache")
        return dict(cache) if isinstance(cache, dict) and cache.get("import_rates") else None

    async def async_save(self, provider: str, cache: dict[str, Any]) -> None:
        await self._store.async_save({"provider": provider, "cache": cache})
