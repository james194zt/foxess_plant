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


def carbon_covers_horizon(
    periods: list[dict[str, Any]] | None,
    *,
    now_ms: int | None = None,
    hours: float = 22.0,
) -> bool:
    """True when carbon forecast extends at least ``hours`` ahead of now."""
    now_ms = now_ms if now_ms is not None else int(dt_util.utcnow().timestamp() * 1000)
    need = now_ms + int(float(hours) * 3600 * 1000)
    return carbon_coverage_end_ms(periods) >= need


def union_carbon_periods(
    *period_lists: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge carbon half-hours by start_ms; later lists win on duplicates."""
    by_start: dict[int, dict[str, Any]] = {}
    for periods in period_lists:
        for row in periods or []:
            if not isinstance(row, dict) or row.get("start_ms") is None:
                continue
            try:
                start_ms = int(row["start_ms"])
            except (TypeError, ValueError):
                continue
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
            value = row.get("value")
        try:
            gco2 = float(value)
        except (TypeError, ValueError):
            gco2 = None
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
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and isinstance(first.get("data"), list):
            return [r for r in first["data"] if isinstance(r, dict)]
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [r for r in data["data"] if isinstance(r, dict)]
    return []


async def fetch_neso_regional_carbon(
    hass: Any,
    postcode: str,
    *,
    hours: int = 48,
) -> list[dict[str, Any]]:
    """Fetch regional carbon forecast from NESO (no auth). Returns normalized periods."""
    outward = outward_postcode(postcode)
    if not outward:
        return []
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)
    now = dt_util.utcnow().replace(second=0, microsecond=0)
    # Align to half-hour boundary.
    minute = 0 if now.minute < 30 else 30
    from_dt = now.replace(minute=minute)
    from_iso = from_dt.strftime("%Y-%m-%dT%H:%MZ")
    window = "fw48h" if int(hours) >= 36 else "fw24h"
    url = f"{NESO_BASE_URL}/regional/intensity/{from_iso}/{window}/postcode/{outward}"
    headers = {"Accept": "application/json", "User-Agent": "FoxESS-Plant/1.0"}
    try:
        async with session.get(url, headers=headers, timeout=30) as resp:
            if resp.status != 200:
                body = await resp.text()
                _LOGGER.warning(
                    "NESO carbon intensity HTTP %s: %s",
                    resp.status,
                    (body or "")[:160],
                )
                return []
            payload = await resp.json(content_type=None)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("NESO carbon intensity fetch failed: %s", err)
        return []
    if not isinstance(payload, dict):
        return []
    rows = _extract_neso_data_rows(payload)
    periods = normalize_neso_carbon_periods(rows)
    periods = trim_carbon_periods(periods)
    _LOGGER.debug(
        "NESO carbon loaded %s half-hours for postcode %s (window %s)",
        len(periods),
        outward,
        window,
    )
    return periods
