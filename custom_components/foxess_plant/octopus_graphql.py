"""Octopus Energy GraphQL client (Greener Nights, carbon forecast, rewards)."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

OCTOPUS_GRAPHQL_URL = "https://api.octopus.energy/v1/graphql/"
OCTOPUS_GRAPHQL_PUBLIC_URL = "https://api.backend.octopus.energy/v1/graphql/"

_OBTAIN_TOKEN_MUTATION = """
mutation ObtainKrakenToken($key: String!) {
  obtainKrakenToken(input: { APIKey: $key }) {
    token
  }
}
"""


class OctopusGraphqlError(Exception):
    """Octopus GraphQL request failed."""


class OctopusGraphqlClient:
    """Minimal GraphQL client for Octopus dashboard extras."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        api_key: str | None = None,
        graphql_url: str = OCTOPUS_GRAPHQL_URL,
    ) -> None:
        self._hass = hass
        self._api_key = api_key.strip() if api_key else ""
        self._graphql_url = graphql_url.rstrip("/") + "/"
        self._session = async_get_clientsession(hass)
        self._token: str | None = None

    async def _obtain_token(self) -> str:
        if not self._api_key:
            raise OctopusGraphqlError("Octopus API key required")
        data = await self._request(
            _OBTAIN_TOKEN_MUTATION,
            variables={"key": self._api_key},
            auth=False,
        )
        block = data.get("obtainKrakenToken")
        if not isinstance(block, dict):
            raise OctopusGraphqlError("Failed to obtain Octopus GraphQL token")
        token = block.get("token")
        if not token:
            raise OctopusGraphqlError("Octopus GraphQL token missing from response")
        self._token = str(token)
        return self._token

    async def _ensure_token(self, *, force_refresh: bool = False) -> str:
        if self._token and not force_refresh:
            return self._token
        return await self._obtain_token()

    async def _request(
        self,
        query: str,
        *,
        variables: dict[str, Any] | None = None,
        auth: bool = False,
        url: str | None = None,
        _retried: bool = False,
    ) -> dict[str, Any]:
        headers = {
            "User-Agent": "FoxESS-Plant/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if auth:
            token = await self._ensure_token(force_refresh=_retried)
            headers["Authorization"] = f"JWT {token}"
        payload = {"query": query, "variables": variables or {}}
        target = url or self._graphql_url
        try:
            async with self._session.post(
                target,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as resp:
                body = await resp.json(content_type=None)
                if not isinstance(body, dict):
                    raise OctopusGraphqlError("Unexpected GraphQL response")
                errors = body.get("errors")
                if errors:
                    first = errors[0] if isinstance(errors, list) and errors else {}
                    extensions = first.get("extensions") if isinstance(first, dict) else {}
                    error_code = extensions.get("errorCode") if isinstance(extensions, dict) else None
                    if (
                        auth
                        and not _retried
                        and error_code in ("KT-CT-1139", "KT-CT-1111", "KT-CT-1143", "KT-CT-1112")
                    ):
                        self._token = None
                        return await self._request(
                            query,
                            variables=variables,
                            auth=auth,
                            url=url,
                            _retried=True,
                        )
                    message = first.get("message") if isinstance(first, dict) else str(errors)
                    raise OctopusGraphqlError(str(message or "GraphQL error"))
                data = body.get("data")
                if not isinstance(data, dict):
                    raise OctopusGraphqlError("GraphQL response missing data")
                return data
        except OctopusGraphqlError:
            raise
        except aiohttp.ClientError as err:
            raise OctopusGraphqlError(f"Octopus GraphQL network error: {err}") from err

    async def fetch_greener_nights_forecast(self) -> list[dict[str, Any]]:
        """Public greener nights forecast (no auth)."""
        query = """
        query GreenerNightsForecast {
          greenerNightsForecast {
            date
            greennessScore
            greennessIndex
            isGreenerNight
          }
        }
        """
        data = await self._request(query, auth=False, url=OCTOPUS_GRAPHQL_PUBLIC_URL)
        rows = data.get("greenerNightsForecast")
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    async def fetch_carbon_intensity(self, postcode: str) -> list[dict[str, Any]]:
        query = """
        query CarbonIntensity($postcode: String!) {
          getProjectedRegionalCarbonIntensity(postcode: $postcode) {
            projectedRegionalCarbonIntensity {
              periodStart
              value
              index
            }
          }
        }
        """
        data = await self._request(query, variables={"postcode": postcode.strip()}, auth=True)
        block = data.get("getProjectedRegionalCarbonIntensity") or {}
        rows = block.get("projectedRegionalCarbonIntensity") if isinstance(block, dict) else None
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    async def fetch_rewards(self, account_number: str) -> dict[str, Any]:
        query = """
        query OctopusRewards($accountNumber: String!) {
          account(accountNumber: $accountNumber) {
            balance
          }
          loyaltyPointsBalance(input: { accountNumber: $accountNumber }) {
            loyaltyPoints
            totalMonetaryAmount
          }
        }
        """
        data = await self._request(
            query,
            variables={"accountNumber": account_number.strip().upper()},
            auth=True,
        )
        account = data.get("account") if isinstance(data.get("account"), dict) else {}
        loyalty = (
            data.get("loyaltyPointsBalance")
            if isinstance(data.get("loyaltyPointsBalance"), dict)
            else {}
        )
        return {
            "account_balance_pence": account.get("balance"),
            "loyalty_points": loyalty.get("loyaltyPoints"),
            "loyalty_monetary_amount": loyalty.get("totalMonetaryAmount"),
        }
