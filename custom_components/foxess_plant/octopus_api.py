"""Octopus Energy REST API client (UK import/export tariffs)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import urlencode

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

OCTOPUS_BASE_URL = "https://api.octopus.energy/v1"
_MAX_SERVER_RETRIES = 3


class OctopusApiError(Exception):
    """Octopus API request failed."""


def summarise_octopus_http_error(status: int, body: str) -> str:
    """Turn Octopus HTML/JSON failure bodies into a short UI-safe message."""
    text = (body or "").strip()
    lower = text.lower()
    if status >= 500 or "<html" in lower or "<!doctype" in lower or "server error" in lower:
        return (
            f"Octopus API temporary server error (HTTP {status}). "
            "This is on Octopus's side — wait a minute and try again."
        )
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("message")
            if detail:
                return f"Octopus API HTTP {status}: {detail}"
    clipped = text[:180].replace("\n", " ")
    return f"Octopus API HTTP {status}: {clipped or 'empty response'}"


class OctopusApiClient:
    """Minimal Octopus HTTP client for Fox Plant tariff polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        api_key: str,
        base_url: str = OCTOPUS_BASE_URL,
    ) -> None:
        self._hass = hass
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._session = async_get_clientsession(hass)
        self._products_cache: list[dict[str, Any]] | None = None

    async def _request(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        query = {k: v for k, v in (params or {}).items() if v is not None}
        suffix = f"?{urlencode(query)}" if query else ""
        url = f"{self._base_url}{path}{suffix}"
        auth_tuple = aiohttp.BasicAuth(self._api_key, "") if auth else None
        headers = {"User-Agent": "FoxESS-Plant/1.0", "Accept": "application/json"}
        last_error: Exception | None = None
        for attempt in range(_MAX_SERVER_RETRIES):
            try:
                async with self._session.get(
                    url,
                    headers=headers,
                    auth=auth_tuple,
                    timeout=aiohttp.ClientTimeout(total=45),
                ) as resp:
                    body = await resp.text()
                    if resp.status == 401:
                        raise OctopusApiError("Invalid Octopus API key")
                    if resp.status == 404:
                        raise OctopusApiError(f"Octopus resource not found: {path}")
                    if resp.status >= 500:
                        last_error = OctopusApiError(summarise_octopus_http_error(resp.status, body))
                        if attempt + 1 < _MAX_SERVER_RETRIES:
                            await asyncio.sleep(1.5 * (attempt + 1))
                            continue
                        raise last_error
                    if resp.status != 200:
                        raise OctopusApiError(summarise_octopus_http_error(resp.status, body))
                    try:
                        data = json.loads(body) if body else {}
                    except json.JSONDecodeError as err:
                        raise OctopusApiError("Unexpected Octopus API response") from err
                    if not isinstance(data, dict):
                        raise OctopusApiError("Unexpected Octopus API response")
                    return data
            except OctopusApiError:
                raise
            except aiohttp.ClientError as err:
                last_error = OctopusApiError(f"Octopus network error: {err}")
                if attempt + 1 < _MAX_SERVER_RETRIES:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                raise last_error from err
        if last_error is not None:
            raise last_error
        raise OctopusApiError("Octopus API request failed")

    async def _paginate(self, path: str, *, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        next_url: str | None = path
        first = True
        while next_url:
            if first:
                payload = await self._request(next_url, params=params)
                first = False
            else:
                if next_url.startswith("http"):
                    async with self._session.get(
                        next_url,
                        headers={"User-Agent": "FoxESS-Plant/1.0"},
                        auth=aiohttp.BasicAuth(self._api_key, ""),
                        timeout=aiohttp.ClientTimeout(total=45),
                    ) as resp:
                        text = await resp.text()
                        if resp.status >= 500:
                            raise OctopusApiError(summarise_octopus_http_error(resp.status, text))
                        if resp.status != 200:
                            raise OctopusApiError(summarise_octopus_http_error(resp.status, text))
                        payload = json.loads(text) if text else {}
                else:
                    payload = await self._request(next_url)
            if not isinstance(payload, dict):
                break
            batch = payload.get("results")
            if isinstance(batch, list):
                rows.extend(item for item in batch if isinstance(item, dict))
            next_raw = payload.get("next")
            next_url = str(next_raw) if next_raw else None
        return rows

    async def get_account(self, account_number: str) -> dict[str, Any]:
        account = account_number.strip().upper()
        if not account:
            raise OctopusApiError("Octopus account number is required")
        try:
            return await self._request(f"/accounts/{account}/")
        except OctopusApiError as err:
            message = str(err)
            if "temporary server error" not in message and "HTTP 5" not in message:
                raise
            _LOGGER.warning("Octopus REST account failed (%s); trying GraphQL fallback", message)
            from .octopus_graphql import OctopusGraphqlClient, OctopusGraphqlError

            gql = OctopusGraphqlClient(self._hass, api_key=self._api_key)
            try:
                return await gql.fetch_account_as_rest(account)
            except OctopusGraphqlError as gql_err:
                raise OctopusApiError(
                    f"{message} GraphQL fallback also failed: {gql_err}"
                ) from gql_err

    async def get_products(self, *, force_refresh: bool = False) -> list[dict[str, Any]]:
        if self._products_cache is not None and not force_refresh:
            return list(self._products_cache)
        rows = await self._paginate("/products/")
        self._products_cache = rows
        return list(rows)

    async def get_product(self, product_code: str) -> dict[str, Any]:
        code = str(product_code or "").strip()
        if not code:
            raise OctopusApiError("Octopus product code is required")
        return await self._request(f"/products/{code}/")

    async def get_unit_rates(
        self,
        product_code: str,
        tariff_code: str,
        *,
        period_from: str | None = None,
        period_to: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if period_from:
            params["period_from"] = period_from
        if period_to:
            params["period_to"] = period_to
        path = f"/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
        return await self._paginate(path, params=params or None)

    async def get_standing_charges(
        self,
        product_code: str,
        tariff_code: str,
        *,
        period_from: str | None = None,
        period_to: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if period_from:
            params["period_from"] = period_from
        if period_to:
            params["period_to"] = period_to
        path = f"/products/{product_code}/electricity-tariffs/{tariff_code}/standing-charges/"
        return await self._paginate(path, params=params or None)

    async def get_electricity_consumption(
        self,
        mpan: str,
        serial: str,
        *,
        period_from: str | None = None,
        period_to: str | None = None,
        page_size: int = 2500,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page_size": page_size}
        if period_from:
            params["period_from"] = period_from
        if period_to:
            params["period_to"] = period_to
        path = f"/electricity-meter-points/{mpan.strip()}/meters/{serial.strip()}/consumption/"
        return await self._paginate(path, params=params)
