"""Persist Solcast PV forecasts (parsed + raw API) across restarts and for history."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SOLCAST_DAILY_INTRADAY_RETENTION_DAYS, SOLCAST_FORECAST_HISTORY_MAX

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 2


def _storage_key(entry_id: str) -> str:
    return f"{DOMAIN}.solcast_forecasts.{entry_id}"


def _normalize_cache_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    cache = deepcopy(snapshot)
    if cache.get("updated_at") and not cache.get("pv_forecast_fetched_at"):
        cache["pv_forecast_fetched_at"] = cache["updated_at"]
    return cache


def _snapshot_has_forecast(snapshot: dict[str, Any] | None) -> bool:
    if not isinstance(snapshot, dict):
        return False
    parsed = snapshot.get("pv_forecast_parsed")
    if not isinstance(parsed, dict):
        return False
    rows = parsed.get("detailed_forecast")
    return isinstance(rows, list) and len(rows) >= 2


def _parse_fetched_at_ms(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value if value > 1e12 else value * 1000)
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        n = float(text)
        return n if n > 1e12 else n * 1000
    parsed = dt_util.parse_datetime(text)
    if parsed is None:
        return None
    return dt_util.as_utc(parsed).timestamp() * 1000


def get_daily_intraday_points(stored: dict[str, Any] | None, day_key: str) -> list[dict[str, float]] | None:
    if not isinstance(stored, dict):
        return None
    daily = stored.get("daily_intraday")
    if not isinstance(daily, dict):
        return None
    rows = daily.get(day_key)
    if not isinstance(rows, list) or len(rows) < 2:
        return None
    out: list[dict[str, float]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        t, v = row.get("t"), row.get("v")
        if isinstance(t, (int, float)) and isinstance(v, (int, float)):
            out.append({"t": float(t), "v": float(v)})
    return out if len(out) >= 2 else None


def cache_from_storage(data: dict[str, Any] | None) -> dict[str, Any]:
    """Rebuild coordinator in-memory cache from stored document."""
    if not data:
        return {}
    current = data.get("current")
    if _snapshot_has_forecast(current):
        return _normalize_cache_snapshot(current)

    history = data.get("history")
    if isinstance(history, list):
        for item in reversed(history):
            if not isinstance(item, dict):
                continue
            snap = item.get("cache")
            if _snapshot_has_forecast(snap):
                _LOGGER.info("Restored Solcast forecast from storage history fallback")
                return _normalize_cache_snapshot(snap)

    if isinstance(current, dict) and current.get("pv_forecast_parsed"):
        return _normalize_cache_snapshot(current)
    return {}


class SolcastForecastStore:
    """JSON store under HA config/.storage for current forecast + poll history."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, _storage_key(entry_id))

    async def async_load(self) -> dict[str, Any]:
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return {"version": STORAGE_VERSION, "current": None, "history": [], "daily_intraday": {}}
        data.setdefault("history", [])
        data.setdefault("daily_intraday", {})
        data["version"] = STORAGE_VERSION
        return data

    async def async_record_poll(self, cache: dict[str, Any]) -> int:
        """Save latest poll as current and append to bounded history. Returns history length."""
        if not _snapshot_has_forecast(cache):
            return SolcastForecastStore.history_count(await self.async_load())
        snapshot = deepcopy(cache)
        fetched_at = snapshot.get("updated_at") or snapshot.get("pv_forecast_fetched_at")
        fetched_ms = _parse_fetched_at_ms(fetched_at)
        data = await self.async_load()
        data["current"] = snapshot
        history: list[dict[str, Any]] = list(data.get("history") or [])
        append = True
        if history:
            last = history[-1]
            last_fetched_ms = _parse_fetched_at_ms(last.get("fetched_at"))
            last_updated = (last.get("cache") or {}).get("updated_at")
            same_updated = last_updated == snapshot.get("updated_at")
            if same_updated and last_fetched_ms and fetched_ms:
                append = (fetched_ms - last_fetched_ms) >= 30 * 60 * 1000
        if append:
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
            "Solcast forecast stored (periods=%s, history=%s, appended=%s)",
            (snapshot.get("pv_forecast_parsed") or {}).get("period_count"),
            len(history),
            append,
        )
        return len(history)

    async def async_merge_daily_intraday(self, updates: dict[str, list[dict[str, float]]]) -> None:
        """Merge per-day 5-minute forecast chart lines (used for Analysis history)."""
        if not updates:
            return
        data = await self.async_load()
        daily: dict[str, list[dict[str, float]]] = dict(data.get("daily_intraday") or {})
        today = dt_util.now().date().isoformat()
        for day_key, points in updates.items():
            if not isinstance(points, list) or len(points) < 2:
                continue
            cleaned = [
                {"t": float(p["t"]), "v": float(p["v"])}
                for p in points
                if isinstance(p, dict) and isinstance(p.get("t"), (int, float)) and isinstance(p.get("v"), (int, float))
            ]
            if len(cleaned) < 2:
                continue
            prev = daily.get(day_key)
            if day_key == today or not isinstance(prev, list) or len(cleaned) >= len(prev):
                daily[day_key] = cleaned
        keys = sorted(daily.keys())[-SOLCAST_DAILY_INTRADAY_RETENTION_DAYS:]
        data["daily_intraday"] = {k: daily[k] for k in keys}
        await self._store.async_save(data)

    @staticmethod
    def history_count(data: dict[str, Any] | None) -> int:
        if not data:
            return 0
        history = data.get("history")
        return len(history) if isinstance(history, list) else 0
