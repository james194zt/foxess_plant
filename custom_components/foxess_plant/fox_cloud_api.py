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

    def __init__(self, message: str, *, errno: int | None = None) -> None:
        super().__init__(message)
        self.errno = errno


def fox_cloud_permission_denied(message: str) -> bool:
    text = str(message or "").lower()
    return "permission" in text and "allow" in text


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
        # Fox API expects literal \r\n characters in the MD5 input, not CRLF bytes.
        signature = hashlib.md5(
            fr"{path}\r\n{self._api_key}\r\n{ts}".encode("utf-8")
        ).hexdigest()
        tz = getattr(self._hass.config, "time_zone", None) or "UTC"
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Token": self._api_key,
            "Signature": signature,
            "Timestamp": ts,
            "Lang": "en",
            "Timezone": tz,
            "User-Agent": "FoxESS-Plant/1.0",
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
                    msg = str(data.get("msg") or f"Fox Cloud error {errno}")
                    try:
                        errno_int = int(errno)
                    except (TypeError, ValueError):
                        errno_int = None
                    raise FoxCloudApiError(msg, errno=errno_int)
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

    async def get_scheduler_flag(self, device_sn: str) -> dict[str, Any]:
        body = {"deviceSN": device_sn.strip()}
        result = await self._post("/op/v1/device/scheduler/get/flag", body)
        return result if isinstance(result, dict) else {}

    async def set_scheduler_flag(self, device_sn: str, *, enable: bool) -> dict[str, Any]:
        body = {"deviceSN": device_sn.strip(), "enable": 1 if enable else 0}
        result = await self._post("/op/v1/device/scheduler/set/flag", body)
        return result if isinstance(result, dict) else {}
