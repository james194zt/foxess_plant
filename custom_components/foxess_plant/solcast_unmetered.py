"""Solcast unmetered test locations (no API quota consumption).

Official list: https://docs.solcast.com.au/ — Unmetered Locations
Same coordinates as solcast-api-python-sdk ``unmetered_locations``.
"""

from __future__ import annotations

from typing import Any

# name -> {latitude, longitude, resource_id}
UNMETERED_LOCATIONS: dict[str, dict[str, Any]] = {
    "Sydney Opera House": {
        "latitude": -33.856784,
        "longitude": 151.215297,
        "resource_id": "ba75-e17a-7374-95ed",
    },
    "Grand Canyon": {
        "latitude": 36.099763,
        "longitude": -112.112485,
        "resource_id": "375f-eb3e-71c0-ef5e",
    },
    "Stonehenge": {
        "latitude": 51.178882,
        "longitude": -1.826215,
        "resource_id": "1a57-6b1f-ec18-c5c8",
    },
    "The Colosseum": {
        "latitude": 41.89021,
        "longitude": 12.492231,
        "resource_id": "5f86-4c8f-2cb3-0215",
    },
    "Giza Pyramid Complex": {
        "latitude": 29.977296,
        "longitude": 31.132496,
        "resource_id": "8d10-f530-af85-5cbb",
    },
    "Taj Mahal": {
        "latitude": 27.175145,
        "longitude": 78.042142,
        "resource_id": "b926-8fd2-ad3f-e4f5",
    },
    "Fort Peck": {
        "latitude": 48.30783,
        "longitude": -105.1017,
        "resource_id": "3ae7-2456-492c-9aba",
    },
    "Goodwin Creek": {
        "latitude": 34.2547,
        "longitude": -89.8729,
        "resource_id": "b787-cf17-e429-ef1d",
    },
}

DEFAULT_UNMETERED_TEST_LOCATION = "Sydney Opera House"

SOLCAST_UNMETERED_DOCS_URL = (
    "https://docs.solcast.com.au/#00577cf8-b43b-4349-b4b5-a5f063916f5a"
)


def unmetered_location_names() -> list[str]:
    return list(UNMETERED_LOCATIONS.keys())


def resolve_unmetered_location(name: str | None = None) -> tuple[str, float, float]:
    """Return (label, latitude, longitude) for a Solcast unmetered test site."""
    label = name if name in UNMETERED_LOCATIONS else DEFAULT_UNMETERED_TEST_LOCATION
    site = UNMETERED_LOCATIONS[label]
    return label, float(site["latitude"]), float(site["longitude"])
