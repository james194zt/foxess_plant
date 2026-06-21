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

    async def _request(
        self,
        query: str,
        *,
        variables: dict[str, Any] | None = None,
        auth: bool = False,
        url: str | None = None,
    ) -> dict[str, Any]:
        headers = {
            "User-Agent": "FoxESS-Plant/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if auth:
            if not self._api_key:
                raise OctopusGraphqlError("Octopus API key required")
        payload = {"query": query, "variables": variables or {}}
        target = url or self._graphql_url
        auth_tuple = aiohttp.BasicAuth(self._api_key, "") if auth else None
        try:
            async with self._session.post(
                target,
                json=payload,
                headers=headers,
                auth=auth_tuple,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as resp:
                body = await resp.json(content_type=None)
                if not isinstance(body, dict):
                    raise OctopusGraphqlError("Unexpected GraphQL response")
                errors = body.get("errors")
                if errors:
                    first = errors[0] if isinstance(errors, list) and errors else {}
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
