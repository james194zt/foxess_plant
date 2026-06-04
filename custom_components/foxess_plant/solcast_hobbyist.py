"""Solcast Home PV (hobbyist) toolkit: rooftop_sites list + per-site forecasts."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import SOLCAST_COORDINATE_DECIMALS
from .models import PlantConfig, SolcastConfig
from .solcast_api import SolcastApiClient, SolcastApiError
from .solcast_pv import RooftopPvRequest, build_rooftop_pv_requests
from .solcast_weather import parse_solcast_coordinates, resolve_coordinates


def _round_coord(value: float) -> float:
    return round(float(value), SOLCAST_COORDINATE_DECIMALS)


def _normalize_azimuth(value: Any) -> int | None:
    try:
        az = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return az % 360


def _tilt_match(a: int, b: int, *, tolerance: int = 2) -> bool:
    return abs(a - b) <= tolerance


def _azimuth_match(a: int, b: int, *, tolerance: int = 5) -> bool:
    aa = a % 360
    bb = b % 360
    diff = abs(aa - bb)
    return diff <= tolerance or diff >= 360 - tolerance


def parse_rooftop_site_list(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Normalize GET /rooftop_sites response to a list of site dicts."""
    if not payload:
        return []
    block = payload.get("sites")
    if isinstance(block, list):
        return [s for s in block if isinstance(s, dict)]
    if isinstance(payload.get("rooftop_sites"), list):
        return [s for s in payload["rooftop_sites"] if isinstance(s, dict)]
    return []


def _site_coordinates(site: dict[str, Any]) -> tuple[float, float] | None:
    parsed = parse_solcast_coordinates(site.get("latitude"), site.get("longitude"))
    return parsed


def _sites_near_coordinates(
    sites: list[dict[str, Any]],
    lat: float,
    lon: float,
) -> list[dict[str, Any]]:
    target = (_round_coord(lat), _round_coord(lon))
    matched: list[dict[str, Any]] = []
    for site in sites:
        coords = _site_coordinates(site)
        if coords is None:
            continue
        if (_round_coord(coords[0]), _round_coord(coords[1])) == target:
            matched.append(site)
    return matched


def _pick_site_for_request(
    candidates: list[dict[str, Any]],
    req: RooftopPvRequest,
    *,
    used_ids: set[str],
) -> dict[str, Any] | None:
    """Match a PV request group to a toolkit site by tilt/azimuth."""
    for site in candidates:
        rid = str(site.get("resource_id") or "").strip()
        if not rid or rid in used_ids:
            continue
        try:
            site_tilt = int(round(float(site.get("tilt", 25))))
        except (TypeError, ValueError):
            site_tilt = 25
        site_az = _normalize_azimuth(site.get("azimuth"))
        if site_az is None:
            continue
        if _tilt_match(site_tilt, req.tilt) and _azimuth_match(site_az, req.azimuth):
            return site
    return None


def match_rooftop_site_bindings(
    sites: list[dict[str, Any]],
    lat: float,
    lon: float,
    requests: list[RooftopPvRequest],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Map each rooftop PV request label to a hobbyist resource_id."""
    if not requests:
        return {}, []
    nearby = _sites_near_coordinates(sites, lat, lon)
    if not nearby:
        return {}, []

    bindings: dict[str, str] = {}
    meta: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    if len(requests) == 1 and len(nearby) == 1:
        site = nearby[0]
        rid = str(site.get("resource_id") or "").strip()
        if rid:
            bindings[requests[0].label] = rid
            meta.append(_site_meta(site, requests[0].label))
        return bindings, meta

    for req in requests:
        site = _pick_site_for_request(nearby, req, used_ids=used_ids)
        if site is None and len(nearby) == 1 and len(requests) == 1:
            site = nearby[0]
        if site is None:
            continue
        rid = str(site.get("resource_id") or "").strip()
        if not rid:
            continue
        bindings[req.label] = rid
        used_ids.add(rid)
        meta.append(_site_meta(site, req.label))

    return bindings, meta


def _site_meta(site: dict[str, Any], label: str) -> dict[str, Any]:
    return {
        "label": label,
        "resource_id": site.get("resource_id"),
        "name": site.get("name"),
        "tilt": site.get("tilt"),
        "azimuth": site.get("azimuth"),
        "capacity_kw": site.get("capacity"),
    }


async def async_list_rooftop_sites(hass: HomeAssistant, solcast: SolcastConfig) -> list[dict[str, Any]]:
    """List Home PV sites from the hobbyist toolkit (does not use daily API quota)."""
    if not solcast.api_key_configured():
        raise SolcastApiError("Solcast API key is not configured")
    client = SolcastApiClient(hass, api_key=solcast.api_key or "")
    payload = await client.list_rooftop_sites()
    return parse_rooftop_site_list(payload)


async def async_resolve_rooftop_bindings(hass: HomeAssistant, plant: PlantConfig) -> dict[str, str]:
    """Resolve hobbyist resource_id(s) for enabled PV strings; updates plant.solcast in place."""
    solcast = plant.solcast
    coords = resolve_coordinates(hass, solcast)
    requests = build_rooftop_pv_requests(plant.pv_config)
    if not requests:
        raise SolcastApiError(
            "Enable at least one PV string under Settings → PV Configuration "
            "(panel count > 0) to fetch forecasts."
        )

    sites = await async_list_rooftop_sites(hass, solcast)
    if not sites:
        raise SolcastApiError(
            "No Home PV systems found on your Solcast account. "
            "Add a site at https://toolkit.solcast.com.au/ then save again."
        )

    bindings, meta = match_rooftop_site_bindings(sites, coords[0], coords[1], requests)
    if not bindings:
        raise SolcastApiError(
            "No Solcast Home PV site matches your saved coordinates and PV tilt/azimuth. "
            "Open each site in the Solcast toolkit and confirm latitude, longitude, tilt, "
            "and azimuth match Fox Plant (PV Configuration + Solcast settings)."
        )

    missing = [r.label for r in requests if r.label not in bindings]
    if missing:
        raise SolcastApiError(
            f"Could not match Solcast site for: {', '.join(missing)}. "
            "Hobbyist accounts support up to two arrays — register each tilt/azimuth "
            "on the Solcast toolkit."
        )

    solcast.rooftop_site_bindings = bindings
    solcast.rooftop_sites_meta = meta
    return bindings
