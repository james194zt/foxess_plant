"""Hildebrand Glow / Glowmarkt Bright API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

GLOW_API_BASE = "https://api.glowmarkt.com/api/v0-1"
GLOW_APPLICATION_ID = "b0f1b774-a586-4f72-9edd-27ead8aa7a8d"


class GlowApiError(Exception):
    """Glowmarkt API request failed."""


class GlowApiClient:
    """Minimal Glowmarkt REST client for Bright individual users."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        token: str | None = None,
        base_url: str = GLOW_API_BASE,
    ) -> None:
        self._hass = hass
        self._session = async_get_clientsession(hass)
        self._base_url = base_url.rstrip("/")
        self._token = token.strip() if token else None

    @staticmethod
    async def authenticate(
        hass: HomeAssistant,
        *,
        username: str,
        password: str,
    ) -> dict[str, Any]:
        """Obtain JWT token from Bright credentials."""
        session = async_get_clientsession(hass)
        url = f"{GLOW_API_BASE}/auth"
        headers = {
            "Content-Type": "application/json",
            "applicationId": GLOW_APPLICATION_ID,
            "User-Agent": "FoxESS-Plant/1.0",
        }
        payload = {"username": username.strip(), "password": password}
        try:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status != 200:
                    message = body.get("message") if isinstance(body, dict) else str(body)
                    raise GlowApiError(message or f"Glow auth HTTP {resp.status}")
                if not isinstance(body, dict) or not body.get("valid"):
                    raise GlowApiError("Glow authentication failed — check Bright username/password")
                token = body.get("token")
                if not token:
                    raise GlowApiError("Glow auth response missing token")
                return body
        except GlowApiError:
            raise
        except aiohttp.ClientError as err:
            raise GlowApiError(f"Glow network error: {err}") from err

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self._token:
            raise GlowApiError("Glow API token required")
        url = f"{self._base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "applicationId": GLOW_APPLICATION_ID,
            "token": self._token,
            "User-Agent": "FoxESS-Plant/1.0",
        }
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45),
                **kwargs,
            ) as resp:
                if resp.status == 401:
                    raise GlowApiError("Glow API token expired — save settings to re-authenticate")
                body = await resp.json(content_type=None)
                if resp.status != 200:
                    message = body.get("message") if isinstance(body, dict) else str(body)
                    raise GlowApiError(message or f"Glow API HTTP {resp.status}")
                return body
        except GlowApiError:
            raise
        except aiohttp.ClientError as err:
            raise GlowApiError(f"Glow network error: {err}") from err

    async def list_resources(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/resource")
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        if isinstance(data, dict):
            rows = data.get("resources") or data.get("data")
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        return []

    async def get_current(self, resource_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/resource/{resource_id}/current")
        return data if isinstance(data, dict) else {}


def classify_glow_resources(resources: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """Pick import/export electricity resource IDs from a /resource listing."""
    import_id: str | None = None
    export_id: str | None = None
    for row in resources:
        rid = row.get("id") or row.get("resourceId")
        if not rid:
            continue
        name = str(row.get("name") or row.get("label") or "").lower()
        rtype = str(row.get("resourceType") or row.get("type") or row.get("resourceTypeId") or "").lower()
        blob = f"{name} {rtype}"
        if "electric" not in blob and "elec" not in blob and "smart" not in blob:
            continue
        if "export" in blob or "generation" in blob or "solar" in blob:
            export_id = str(rid)
        elif "import" in blob or "consumption" in blob or "meter" in blob:
            import_id = str(rid)
    if import_id is None:
        for row in resources:
            rid = row.get("id") or row.get("resourceId")
            name = str(row.get("name") or "").lower()
            if rid and "import" in name:
                import_id = str(rid)
                break
    return import_id, export_id
