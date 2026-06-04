"""Solcast hobbyist API client (rooftop + radiation/weather endpoints)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

SOLCAST_BASE_URL = "https://api.solcast.com.au"
LIVE_RADIATION_WEATHER = "/data/live/radiation_and_weather"
LIVE_ROOFTOP_PV = "/data/live/rooftop_pv_power"
FORECAST_RADIATION_WEATHER = "/data/forecast/radiation_and_weather"
FORECAST_ROOFTOP_PV = "/data/forecast/rooftop_pv_power"

DEFAULT_LIVE_OUTPUT = (
    "air_temp",
    "cloud_opacity",
    "precipitation_rate",
    "cape",
    "weather_type",
    "wind_speed_10m",
    "relative_humidity",
)

DEFAULT_FORECAST_OUTPUT = (
    "air_temp",
    "cloud_opacity",
    "precipitation_rate",
    "cape",
    "weather_type",
)


class SolcastApiError(Exception):
    """Solcast API request failed."""


class SolcastApiClient:
    """Minimal Solcast HTTP client for Fox Plant (hobbyist / rooftop)."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        api_key: str,
        base_url: str = SOLCAST_BASE_URL,
    ) -> None:
        self._hass = hass
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._session = async_get_clientsession(hass)

    async def _request(
        self,
        path: str,
        params: dict[str, Any],
        *,
        fallback_output: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        query = {k: v for k, v in params.items() if v is not None}
        url = f"{self._base_url}{path}?{urlencode(query)}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": "FoxESS-Plant/1.0",
        }
        try:
            async with self._session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                body = await resp.text()
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    if not isinstance(data, dict):
                        raise SolcastApiError("Unexpected Solcast response shape")
                    return data
                if (
                    resp.status == 400
                    and fallback_output
                    and "weather_type" in str(query.get("output_parameters", ""))
                ):
                    _LOGGER.debug("Retrying Solcast without weather_type parameter")
                    retry = dict(query)
                    retry["output_parameters"] = ",".join(fallback_output)
                    return await self._request(path, retry, fallback_output=None)
                raise SolcastApiError(f"Solcast HTTP {resp.status}: {body[:240]}")
        except aiohttp.ClientError as err:
            raise SolcastApiError(str(err)) from err

    async def live_radiation_and_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        period: str = "PT30M",
    ) -> dict[str, Any]:
        """Current/live irradiance and weather (1 API request)."""
        return await self._request(
            LIVE_RADIATION_WEATHER,
            {
                "latitude": latitude,
                "longitude": longitude,
                "period": period,
                "output_parameters": ",".join(DEFAULT_LIVE_OUTPUT),
                "format": "json",
            },
            fallback_output=tuple(p for p in DEFAULT_LIVE_OUTPUT if p != "weather_type"),
        )

    async def forecast_radiation_and_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        hours: int = 48,
        period: str = "PT30M",
    ) -> dict[str, Any]:
        """Forecast irradiance and weather (1 API request)."""
        return await self._request(
            FORECAST_RADIATION_WEATHER,
            {
                "latitude": latitude,
                "longitude": longitude,
                "hours": hours,
                "period": period,
                "output_parameters": ",".join(DEFAULT_FORECAST_OUTPUT),
                "format": "json",
            },
            fallback_output=tuple(p for p in DEFAULT_FORECAST_OUTPUT if p != "weather_type"),
        )

    async def live_rooftop_pv_power(
        self,
        *,
        latitude: float,
        longitude: float,
        capacity_kw: float,
        tilt: int = 25,
        azimuth: int = 180,
        loss_factor: float = 0.9,
        period: str = "PT30M",
    ) -> dict[str, Any]:
        """Live/nowcast rooftop PV power (1 API request)."""
        return await self._request(
            LIVE_ROOFTOP_PV,
            {
                "latitude": latitude,
                "longitude": longitude,
                "capacity": capacity_kw,
                "tilt": tilt,
                "azimuth": azimuth,
                "loss_factor": loss_factor,
                "period": period,
                "output_parameters": "pv_power_rooftop",
                "format": "json",
            },
        )

    async def forecast_rooftop_pv_power(
        self,
        *,
        latitude: float,
        longitude: float,
        capacity_kw: float,
        tilt: int = 25,
        azimuth: int = 0,
        loss_factor: float = 0.9,
        period: str = "PT30M",
        hours: int = 48,
    ) -> dict[str, Any]:
        """Rooftop PV power forecast (1 API request) — hobbyist endpoint."""
        return await self._request(
            FORECAST_ROOFTOP_PV,
            {
                "latitude": latitude,
                "longitude": longitude,
                "capacity": capacity_kw,
                "tilt": tilt,
                "azimuth": azimuth,
                "loss_factor": loss_factor,
                "period": period,
                "hours": hours,
                "output_parameters": "pv_power_rooftop",
                "format": "json",
            },
        )
