"""Solcast rooftop PV forecast parsing and PV system request building."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .models import PlantConfig, PvStringConfig, PvSystemConfig


@dataclass(frozen=True)
class RooftopPvRequest:
    """One Solcast rooftop_pv_power API call (may represent combined strings)."""

    label: str
    capacity_kw: float
    tilt: int
    azimuth: int
    loss_factor: float
    string_keys: tuple[str, ...]


def _clamp_tilt(value: Any, default: int = 25) -> int:
    try:
        tilt = int(value)
    except (TypeError, ValueError):
        tilt = default
    return max(0, min(90, tilt))


def _clamp_azimuth(value: Any, default: int = 180) -> int:
    try:
        azimuth = int(value)
    except (TypeError, ValueError):
        azimuth = default
    return max(0, min(359, azimuth))


def pv_string_loss_factor(string: PvStringConfig) -> float:
    return max(0.01, min(1.0, string.efficiency_factor / 100.0))


def build_rooftop_pv_requests(pv_config: PvSystemConfig) -> list[RooftopPvRequest]:
    """Group enabled PV strings by tilt/azimuth to minimise API calls (max 2 on hobbyist)."""
    enabled: list[tuple[str, PvStringConfig]] = []
    for key in ("pv1", "pv2"):
        string = getattr(pv_config, key)
        if string.enabled and string.panel_count > 0:
            enabled.append((key, string))
    if not enabled:
        return []

    groups: dict[tuple[int, int], list[tuple[str, PvStringConfig]]] = {}
    for key, string in enabled:
        tilt = _clamp_tilt(string.tilt)
        azimuth = _clamp_azimuth(string.azimuth)
        groups.setdefault((tilt, azimuth), []).append((key, string))

    requests: list[RooftopPvRequest] = []
    for (tilt, azimuth), items in sorted(groups.items()):
        total_w = sum(s.effective_dc_w for _, s in items)
        capacity_kw = max(0.1, total_w / 1000.0)
        weighted_loss = sum(s.effective_dc_w * pv_string_loss_factor(s) for _, s in items) / total_w
        keys = tuple(k for k, _ in items)
        label = keys[0] if len(keys) == 1 else "+".join(keys)
        requests.append(
            RooftopPvRequest(
                label=label,
                capacity_kw=round(capacity_kw, 3),
                tilt=tilt,
                azimuth=azimuth,
                loss_factor=round(weighted_loss, 3),
                string_keys=keys,
            )
        )
    return requests


def forecast_hours_until_local_midnight(hass: HomeAssistant, *, buffer_hours: int = 2) -> int:
    """Hours of PV forecast to request (rest of local day, capped)."""
    now = dt_util.now()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    if end <= now:
        end += timedelta(days=1)
    hours = int((end - now).total_seconds() // 3600) + buffer_hours
    return max(1, min(hours, 48))


def _series_rows(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    for key in ("forecasts", "estimated_actuals", "data"):
        block = payload.get(key)
        if isinstance(block, list):
            return [row for row in block if isinstance(row, dict)]
    return []


def _period_key(row: dict[str, Any]) -> str | None:
    for field in ("period_end", "period_start"):
        raw = row.get(field)
        if raw:
            return str(raw)
    return None


def _power_kw(row: dict[str, Any]) -> float | None:
    for field in ("pv_estimate", "pv_power_rooftop", "power", "pv_power"):
        raw = row.get(field)
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        return value
    return None


def merge_rooftop_forecasts(
    payloads: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Sum kW by period across one or more rooftop PV API responses."""
    by_period: dict[str, float] = {}
    for _label, payload in payloads:
        for row in _series_rows(payload):
            period = _period_key(row)
            power = _power_kw(row)
            if period is None or power is None:
                continue
            by_period[period] = by_period.get(period, 0.0) + power
    return [
        {"period_start": period, "period_end": period, "pv_estimate": round(kw, 4)}
        for period, kw in sorted(by_period.items())
    ]


def parse_detailed_forecast(
    payloads: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Build HA-sensor-compatible detailed forecast structure."""
    per_site: dict[str, list[dict[str, Any]]] = {}
    for label, payload in payloads:
        rows: list[dict[str, Any]] = []
        for row in _series_rows(payload):
            period = _period_key(row)
            power = _power_kw(row)
            if period is None or power is None:
                continue
            rows.append(
                {
                    "period_start": period,
                    "period_end": row.get("period_end") or period,
                    "pv_estimate": power,
                }
            )
        if rows:
            per_site[f"detailedForecast_{label}"] = rows

    combined = merge_rooftop_forecasts(payloads)
    now_kw = None
    if combined:
        now_kw = combined[0]["pv_estimate"]
    energy_remaining = sum(
        row["pv_estimate"] * 0.5 for row in combined
    )  # PT30M ≈ 0.5h per interval; refined below

    period_hours = 0.5
    energy_remaining = 0.0
    for i, row in enumerate(combined):
        if i + 1 < len(combined):
            t0 = _parse_dt(row["period_start"])
            t1 = _parse_dt(combined[i + 1]["period_start"])
            if t0 and t1:
                period_hours = max(0.083, (t1 - t0).total_seconds() / 3600.0)
        energy_remaining += row["pv_estimate"] * period_hours

    return {
        "detailed_forecast": combined,
        "detailed_forecast_by_site": per_site,
        "power_now_kw": now_kw,
        "energy_remaining_kwh": round(energy_remaining, 2) if combined else None,
        "period_count": len(combined),
    }


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        return None
    return dt_util.as_utc(parsed) if parsed.tzinfo else parsed.replace(tzinfo=dt_util.UTC)


def rooftop_requests_summary(plant: PlantConfig) -> list[dict[str, Any]]:
    return [
        {
            "label": req.label,
            "string_keys": list(req.string_keys),
            "capacity_kw": req.capacity_kw,
            "tilt": req.tilt,
            "azimuth": req.azimuth,
            "loss_factor": req.loss_factor,
        }
        for req in build_rooftop_pv_requests(plant.pv_config)
    ]
