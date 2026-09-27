"""House load profile from recorder history — pure stdlib (no Home Assistant import).

Input is the hourly cumulative ``sum`` statistic of the inverter's load energy
counter. Output is 48 half-hour kWh values per day type, used by the planner.
"""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from statistics import median
from typing import Any

MAX_HOURLY_KWH = 25.0  # drop counter resets / spikes


def hourly_consumption(points: list[dict[str, Any]]) -> list[tuple[datetime, float]]:
    """Diff cumulative hourly sums into (hour_start_utc, kWh) pairs.

    ``points`` rows look like ``{"start": epoch_seconds, "mean": cumulative_sum}``
    (the shape returned by ``websocket_api._fetch_statistics_points``).
    """
    ordered = sorted(
        (p for p in points if p.get("start") is not None and p.get("mean") is not None),
        key=lambda p: float(p["start"]),
    )
    out: list[tuple[datetime, float]] = []
    for prev, cur in zip(ordered, ordered[1:]):
        if float(cur["start"]) - float(prev["start"]) != 3600:
            continue
        kwh = float(cur["mean"]) - float(prev["mean"])
        if kwh < 0 or kwh > MAX_HOURLY_KWH:
            continue
        # A statistics row's sum is the counter at the END of its hour.
        out.append((datetime.fromtimestamp(float(cur["start"]), tz=timezone.utc), kwh))
    return out


def build_load_profile(
    hourly: list[tuple[datetime, float]],
    tz: tzinfo,
    *,
    min_days_per_type: int = 4,
) -> dict[str, Any] | None:
    """Median kWh per local half-hour; split weekday/weekend when there's enough history."""
    buckets: dict[str, list[list[float]]] = {
        "weekday": [[] for _ in range(24)],
        "weekend": [[] for _ in range(24)],
        "all": [[] for _ in range(24)],
    }
    days: dict[str, set] = {"weekday": set(), "weekend": set(), "all": set()}
    for start, kwh in hourly:
        local = start.astimezone(tz)
        kind = "weekend" if local.weekday() >= 5 else "weekday"
        for key in (kind, "all"):
            buckets[key][local.hour].append(kwh)
            days[key].add(local.date())
    if not days["all"]:
        return None

    def halves(hours: list[list[float]]) -> list[float] | None:
        if any(not h for h in hours):
            return None
        out: list[float] = []
        for values in hours:
            half = round(median(values) / 2.0, 4)
            out.extend([half, half])
        return out

    profile: dict[str, Any] = {"days": len(days["all"])}
    all_profile = halves(buckets["all"])
    if all_profile is None:
        return None
    profile["all"] = all_profile
    for key in ("weekday", "weekend"):
        if len(days[key]) >= min_days_per_type:
            values = halves(buckets[key])
            if values is not None:
                profile[key] = values
    profile["daily_kwh"] = round(sum(all_profile), 2)
    return profile


def average_load_kw(profile: dict[str, Any] | None, fallback_kw: float) -> float:
    if not profile or not isinstance(profile.get("all"), list):
        return max(0.0, fallback_kw)
    return max(0.0, sum(float(v) for v in profile["all"]) / 24.0)
