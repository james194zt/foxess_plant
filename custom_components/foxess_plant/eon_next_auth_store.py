"""Persist the rotating E.ON Next (Auth0) refresh token so it survives restarts."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1


class EonNextAuthStore:
    """Latest refresh token for the token chain started by one pasted token (``seed``)."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"foxess_plant.eon_next_auth.{entry_id}")

    async def async_token_for_seed(self, seed: str) -> str | None:
        data: Any = await self._store.async_load()
        if isinstance(data, dict) and data.get("seed") == seed and data.get("refresh_token"):
            return str(data["refresh_token"])
        return None

    async def async_save_token(self, seed: str, refresh_token: str) -> None:
        await self._store.async_save({"seed": seed, "refresh_token": refresh_token})
