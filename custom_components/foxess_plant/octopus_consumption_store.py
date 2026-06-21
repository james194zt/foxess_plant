"""Persist Octopus smart-meter half-hourly electricity consumption."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
# ~40 days of half-hourly intervals
CONSUMPTION_HISTORY_MAX = 40 * 48


def _storage_key(entry_id: str) -> str:
    return f"foxess_plant.octopus_consumption.{entry_id}"


class OctopusConsumptionStore:
    """JSON store for import/export half-hourly meter readings."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, _storage_key(entry_id))

    async def async_load(self) -> dict[str, Any]:
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return {
                "version": STORAGE_VERSION,
                "import": [],
                "export": [],
                "last_fetch_at": None,
            }
        data.setdefault("import", [])
        data.setdefault("export", [])
        return data

    @staticmethod
    def _merge_rows(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_start: dict[int, dict[str, Any]] = {}
        for row in existing:
            if isinstance(row, dict) and row.get("start_ms") is not None:
                by_start[int(row["start_ms"])] = row
        for row in incoming:
            if isinstance(row, dict) and row.get("start_ms") is not None:
                by_start[int(row["start_ms"])] = row
        merged = sorted(by_start.values(), key=lambda item: int(item["start_ms"]))
        if len(merged) > CONSUMPTION_HISTORY_MAX:
            merged = merged[-CONSUMPTION_HISTORY_MAX:]
        return merged

    async def async_merge_rows(
        self,
        *,
        import_rows: list[dict[str, Any]] | None = None,
        export_rows: list[dict[str, Any]] | None = None,
        fetched_at: str | None = None,
    ) -> dict[str, Any]:
        """Merge new half-hour rows and persist. Returns updated store dict."""
        data = await self.async_load()
        if import_rows:
            data["import"] = self._merge_rows(list(data.get("import") or []), import_rows)
        if export_rows:
            data["export"] = self._merge_rows(list(data.get("export") or []), export_rows)
        if fetched_at:
            data["last_fetch_at"] = fetched_at
        await self._store.async_save(data)
        _LOGGER.debug(
            "Octopus consumption stored (import=%s export=%s)",
            len(data.get("import") or []),
            len(data.get("export") or []),
        )
        return data

    @staticmethod
    def rows_since(rows: list[dict[str, Any]], *, start_ms: int) -> list[dict[str, Any]]:
        return [r for r in rows if isinstance(r, dict) and int(r.get("start_ms") or 0) >= start_ms]

    @staticmethod
    def latest_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not rows:
            return None
        return max(rows, key=lambda r: int(r.get("start_ms") or 0))
