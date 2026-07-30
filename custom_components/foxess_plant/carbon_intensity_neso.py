"""National Grid / NESO Carbon Intensity API helpers (GB regional forecast)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

NESO_BASE_URL = "https://api.carbonintensity.org.uk"


def outward_postcode(postcode: str | None) -> str | None:
    """Outward code only (e.g. SW1A 1AA → SW1A) for the regional CI API."""
    raw = str(postcode or "").strip().upper().replace(" ", "")
    if len(raw) < 2:
        return None
    # UK outward is all but last 3 inward characters.
    if len(raw) > 3:
        return raw[:-3]
    return raw


def carbon_coverage_end_ms(periods: list[dict[str, Any]] | None) -> int:
    end = 0
    for row in periods or []:
        try:
            end = max(end, int(row.get("end_ms") or 0))
        except (TypeError, ValueError):
            continue
    return end


def carbon_valued_count(periods: list[dict[str, Any]] | None) -> int:
    return sum(
        1
        for row in periods or []
        if isinstance(row, dict) and row.get("gco2_per_kwh") is not None
    )


def carbon_covers_horizon(
    periods: list[dict[str, Any]] | None,
    *,
    now_ms: int | None = None,
    hours: float = 22.0,
) -> bool:
    """True when valued carbon forecast extends at least ``hours`` ahead of now."""
    now_ms = now_ms if now_ms is not None else int(dt_util.utcnow().timestamp() * 1000)
    need = now_ms + int(float(hours) * 3600 * 1000)
    if carbon_coverage_end_ms(periods) < need:
        return False
    # Require enough valued half-hours so empty/null Octopus tails cannot fake coverage.
    return carbon_valued_count(periods) >= max(36, int(float(hours) * 2) - 8)


def union_carbon_periods(
    *period_lists: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge carbon half-hours by start_ms.

    Later lists win on duplicates, but a valued (gCO₂) row never loses to a null-valued one.
    """
    by_start: dict[int, dict[str, Any]] = {}
    for periods in period_lists:
        for row in periods or []:
            if not isinstance(row, dict) or row.get("start_ms") is None:
                continue
            try:
                start_ms = int(row["start_ms"])
            except (TypeError, ValueError):
                continue
            existing = by_start.get(start_ms)
            if existing is None:
                by_start[start_ms] = row
                continue
            existing_val = existing.get("gco2_per_kwh")
            incoming_val = row.get("gco2_per_kwh")
            if existing_val is None and incoming_val is not None:
                by_start[start_ms] = row
            elif incoming_val is not None or existing_val is None:
                by_start[start_ms] = row
    return trim_carbon_periods([by_start[k] for k in sorted(by_start.keys())])


def trim_carbon_periods(
    periods: list[dict[str, Any]] | None,
    *,
    now_ms: int | None = None,
    past_hours: float = 12.0,
    future_hours: float = 54.0,
) -> list[dict[str, Any]]:
    """Keep a rolling window so unions cannot grow forever and bloat plant_state."""
    rows = [r for r in (periods or []) if isinstance(r, dict) and r.get("start_ms") is not None]
    if not rows:
        return []
    now_ms = now_ms if now_ms is not None else int(dt_util.utcnow().timestamp() * 1000)
    lo = now_ms - int(float(past_hours) * 3600 * 1000)
    hi = now_ms + int(float(future_hours) * 3600 * 1000)
    trimmed: list[dict[str, Any]] = []
    for row in rows:
        try:
            start_ms = int(row["start_ms"])
            end_ms = int(row["end_ms"]) if row.get("end_ms") is not None else start_ms + 30 * 60 * 1000
        except (TypeError, ValueError):
            continue
        if end_ms < lo or start_ms > hi:
            continue
        trimmed.append(row)
    trimmed.sort(key=lambda item: int(item["start_ms"]))
    return trimmed


def normalize_neso_carbon_periods(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map NESO regional intensity rows into Fox Plant carbon_periods shape."""
    from .octopus_greener import is_low_carbon_green, low_carbon_score_from_gco2

    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        start = _parse_iso_dt(row.get("from") or row.get("periodStart"))
        end = _parse_iso_dt(row.get("to"))
        if start is None:
            continue
        if end is None:
            end = start + timedelta(minutes=30)
        intensity = row.get("intensity") if isinstance(row.get("intensity"), dict) else {}
        value = intensity.get("forecast")
        if value is None:
            value = intensity.get("actual")
        if value is None:
            value = row.get("value")
        try:
            gco2 = float(value)
        except (TypeError, ValueError):
            gco2 = None
        if gco2 is None:
            continue
        score = low_carbon_score_from_gco2(gco2)
        out.append(
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "start_ms": int(start.timestamp() * 1000),
                "end_ms": int(end.timestamp() * 1000),
                "gco2_per_kwh": gco2,
                "low_carbon_score": score,
                "index": intensity.get("index") or row.get("index"),
                "is_green": is_low_carbon_green(gco2=gco2, score=score),
                "source": "neso",
            }
        )
    out.sort(key=lambda item: item["start_ms"])
    return out


def _parse_iso_dt(raw: Any) -> Any:
    if not raw:
        return None
    try:
        parsed = dt_util.parse_datetime(str(raw))
    except (TypeError, ValueError):
        parsed = None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt_util.UTC)
    return dt_util.as_utc(parsed)


def _extract_neso_data_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    # Regional fw* responses: {"data": {"regionid": …, "data": [half-hours…]}}
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [r for r in data["data"] if isinstance(r, dict)]
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and isinstance(first.get("data"), list):
            return [r for r in first["data"] if isinstance(r, dict)]
        return [r for r in data if isinstance(r, dict)]
    return []


async def _fetch_neso_json(hass: Any, url: str) -> dict[str, Any] | None:
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)
    headers = {"Accept": "application/json", "User-Agent": "FoxESS-Plant/1.0"}
    try:
        async with session.get(url, headers=headers, timeout=30) as resp:
            if resp.status != 200:
                body = await resp.text()
                _LOGGER.warning(
                    "NESO carbon intensity HTTP %s for %s: %s",
                    resp.status,
                    url,
                    (body or "")[:160],
                )
                return None
            payload = await resp.json(content_type=None)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("NESO carbon intensity fetch failed (%s): %s", url, err)
        return None
    return payload if isinstance(payload, dict) else None


def _neso_from_iso() -> str:
    now = dt_util.utcnow().replace(second=0, microsecond=0)
    minute = 0 if now.minute < 30 else 30
    from_dt = now.replace(minute=minute)
    return from_dt.strftime("%Y-%m-%dT%H:%MZ")


async def fetch_neso_regional_carbon(
    hass: Any,
    postcode: str,
    *,
    hours: int = 48,
) -> list[dict[str, Any]]:
    """Fetch regional carbon forecast from NESO (no auth). Returns normalized periods."""
    outward = outward_postcode(postcode)
    from_iso = _neso_from_iso()
    window = "fw48h" if int(hours) >= 36 else "fw24h"
    periods: list[dict[str, Any]] = []
    if outward:
        url = f"{NESO_BASE_URL}/regional/intensity/{from_iso}/{window}/postcode/{outward}"
        payload = await _fetch_neso_json(hass, url)
        if payload:
            periods = normalize_neso_carbon_periods(_extract_neso_data_rows(payload))
    if not carbon_covers_horizon(periods, hours=min(22, float(hours))):
        # Regional empty / truncated — national intensity still covers the Agile window.
        url = f"{NESO_BASE_URL}/intensity/{from_iso}/{window}"
        payload = await _fetch_neso_json(hass, url)
        if payload:
            national = normalize_neso_carbon_periods(_extract_neso_data_rows(payload))
            for row in national:
                row["source"] = "neso-national"
            periods = union_carbon_periods(periods, national)
            _LOGGER.info(
                "NESO national carbon fallback loaded %s half-hours (postcode %s)",
                len(national),
                outward or "—",
            )
    periods = trim_carbon_periods(periods)
    _LOGGER.debug(
        "NESO carbon loaded %s half-hours for postcode %s (window %s)",
        len(periods),
        outward or "national",
        window,
    )
    return periods


async def ensure_neso_carbon_fill(
    hass: Any,
    periods: list[dict[str, Any]] | None,
    postcode: str | None,
    *,
    hours: float = 22.0,
) -> tuple[list[dict[str, Any]], str | None]:
    """Union NESO forecast when Octopus / cached carbon is too short for the price overlay."""
    current = list(periods or [])
    if carbon_covers_horizon(current, hours=hours):
        return current, None
    if not postcode:
        return current, None
    try:
        neso = await fetch_neso_regional_carbon(hass, postcode, hours=48)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("NESO carbon ensure failed: %s", err)
        return current, None
    if not neso:
        return current, None
    merged = union_carbon_periods(neso, current)
    source = "octopus+neso" if current else "neso"
    _LOGGER.info(
        "NESO carbon fill: %s → %s half-hours (valued %s → %s)",
        len(current),
        len(merged),
        carbon_valued_count(current),
        carbon_valued_count(merged),
    )
    return merged, source
