"""FoxESS Cloud Open API client (signed requests)."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

FOX_CLOUD_BASE = "https://www.foxesscloud.com"
FOX_API_DOCS_URL = "https://www.foxesscloud.com/i18n/en/OpenApiDocument.html"


class FoxCloudApiError(Exception):
    """FoxESS Cloud API request failed."""


class FoxCloudClient:
    """Minimal FoxESS Cloud Open API client."""

    def __init__(self, hass: HomeAssistant, *, api_key: str) -> None:
        key = str(api_key or "").strip()
        if not key:
            raise FoxCloudApiError("Fox Cloud API key required")
        self._hass = hass
        self._session = async_get_clientsession(hass)
        self._api_key = key

    def _headers(self, path: str) -> dict[str, str]:
        ts = str(int(time.time() * 1000))
        signature = hashlib.md5(f"{path}\r\n{self._api_key}\r\n{ts}".encode()).hexdigest()
        return {
            "Content-Type": "application/json",
            "token": self._api_key,
            "signature": signature,
            "timestamp": ts,
            "lang": "en",
        }

    async def _post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{FOX_CLOUD_BASE}{path}"
        headers = self._headers(path)
        try:
            async with self._session.post(
                url,
                json=body or {},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as resp:
                data = await resp.json(content_type=None)
                if resp.status != 200:
                    message = data.get("msg") if isinstance(data, dict) else str(data)
                    raise FoxCloudApiError(message or f"Fox Cloud HTTP {resp.status}")
                if not isinstance(data, dict):
                    raise FoxCloudApiError("Fox Cloud returned invalid JSON")
                errno = data.get("errno", 0)
                if errno not in (0, None):
                    raise FoxCloudApiError(str(data.get("msg") or f"Fox Cloud error {errno}"))
                return data.get("result")
        except FoxCloudApiError:
            raise
        except aiohttp.ClientError as err:
            raise FoxCloudApiError(f"Fox Cloud network error: {err}") from err

    async def list_devices(self, *, page: int = 1, size: int = 10) -> list[dict[str, Any]]:
        result = await self._post("/op/v0/device/list", {"currentPage": page, "pageSize": size})
        if isinstance(result, dict):
            rows = result.get("data") or result.get("list") or []
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        if isinstance(result, list):
            return [row for row in result if isinstance(row, dict)]
        return []

    async def get_battery_heating(self, sn: str) -> dict[str, Any]:
        result = await self._post("/op/v0/device/batteryHeating/get", {"sn": sn.strip()})
        return result if isinstance(result, dict) else {"dataList": []}

    async def set_battery_heating(self, sn: str, payload: dict[str, Any]) -> None:
        body = {"sn": sn.strip(), **payload}
        await self._post("/op/v0/device/batteryHeating/set", body)
