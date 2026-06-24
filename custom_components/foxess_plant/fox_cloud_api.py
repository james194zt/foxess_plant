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


def format_fox_cloud_error(err: FoxCloudApiError) -> str:
    message = str(err)
    if err.errno is not None:
        return f"{message} (Fox API {err.errno})"
    return message


def match_fox_device_sn(devices: list[dict[str, Any]], sn: str) -> str | None:
    """Map PCS/module/configured SN to the Fox Cloud inverter deviceSN."""
    needle = str(sn or "").strip().upper()
    if not needle:
        return None
    for row in devices:
        if not isinstance(row, dict):
            continue
        device_sn = str(row.get("deviceSN") or "").strip()
        module_sn = str(row.get("moduleSN") or "").strip()
        if needle in {device_sn.upper(), module_sn.upper()}:
            return device_sn or None
    return None


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
        ts = str(round(time.time() * 1000))
        # Docs: md5(path + "\r\n" + token + "\r\n" + timestamp) — literal \r\n in the string.
        signature = hashlib.md5(
            fr"{path}\r\n{self._api_key}\r\n{ts}".encode("utf-8")
        ).hexdigest()
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

    async def list_devices(self, *, page: int = 1, size: int = 500) -> list[dict[str, Any]]:
        result = await self._post("/op/v0/device/list", {"currentPage": page, "pageSize": size})
        if isinstance(result, dict):
            rows = result.get("data") or result.get("list") or []
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        if isinstance(result, list):
            return [row for row in result if isinstance(row, dict)]
        return []

    async def get_scheduler_schedule(self, device_sn: str) -> dict[str, Any]:
        """Read scheduler master switch from V3/V2/V1/V0 schedule endpoints."""
        body = {"deviceSN": device_sn.strip()}
        paths = (
            "/op/v3/device/scheduler/get",
            "/op/v2/device/scheduler/get",
            "/op/v1/device/scheduler/get",
            "/op/v0/device/scheduler/get",
        )
        last: FoxCloudApiError | None = None
        for index, path in enumerate(paths):
            try:
                result = await self._post(path, body)
                if isinstance(result, dict):
                    return result
            except FoxCloudApiError as err:
                last = err
                if index + 1 < len(paths) and err.errno in (41200, 41203, 40256, 41811):
                    _LOGGER.debug(
                        "Fox scheduler get %s failed (%s), trying fallback path",
                        path,
                        err,
                    )
                    continue
                raise
        if last:
            raise last
        return {}

    async def get_battery_heating(self, sn: str) -> dict[str, Any]:
        result = await self._post("/op/v0/device/batteryHeating/get", {"sn": sn.strip()})
        return result if isinstance(result, dict) else {"dataList": []}

    async def set_battery_heating(self, sn: str, payload: dict[str, Any]) -> None:
        body = {"sn": sn.strip(), **payload}
        await self._post("/op/v0/device/batteryHeating/set", body)

    async def _post_scheduler_paths(
        self,
        paths: tuple[str, ...],
        body: dict[str, Any],
        *,
        operation: str,
    ) -> Any:
        last: FoxCloudApiError | None = None
        for index, path in enumerate(paths):
            try:
                return await self._post(path, body)
            except FoxCloudApiError as err:
                last = err
                if index + 1 < len(paths) and err.errno in (41200, 41203, 40256, 41811):
                    _LOGGER.debug(
                        "Fox scheduler %s %s failed (%s), trying fallback path",
                        operation,
                        path,
                        err,
                    )
                    continue
                raise
        if last:
            raise last
        return None

    async def get_scheduler_flag(self, device_sn: str) -> dict[str, Any]:
        body = {"deviceSN": device_sn.strip()}
        flag_paths = (
            "/op/v1/device/scheduler/get/flag",
            "/op/v0/device/scheduler/get/flag",
        )
        last: FoxCloudApiError | None = None
        try:
            result = await self._post_scheduler_paths(flag_paths, body, operation="get/flag")
            if isinstance(result, dict) and result:
                return result
        except FoxCloudApiError as err:
            last = err
            if err.errno not in (41200, 41203, 40256, 41811):
                raise
        schedule = await self.get_scheduler_schedule(device_sn)
        if schedule:
            enable = schedule.get("enable")
            if enable is not None:
                return {"support": True, "enable": enable}
        if last:
            raise last
        return {}

    async def set_scheduler_flag(self, device_sn: str, *, enable: bool) -> dict[str, Any]:
        body = {"deviceSN": device_sn.strip(), "enable": 1 if enable else 0}
        paths = (
            "/op/v1/device/scheduler/set/flag",
            "/op/v0/device/scheduler/set/flag",
            "/op/v0/device/scheduler/set",
        )
        result = await self._post_scheduler_paths(paths, body, operation="set/flag")
        return result if isinstance(result, dict) else {}
