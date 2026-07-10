"""Intraday physics insight strings from recorder performance series."""

from __future__ import annotations

from typing import Any

CLIPPING_THRESHOLD = 0.98
BUCKET_MINUTES = 5


def _sorted_points(rows: list[dict[str, Any]] | None) -> list[dict[str, float]]:
    pts: list[dict[str, float]] = []
    for row in rows or []:
        t = row.get("t")
        v = row.get("v")
        if t is None or v is None:
            continue
        try:
            pts.append({"t": float(t), "v": float(v)})
        except (TypeError, ValueError):
            continue
    return sorted(pts, key=lambda p: p["t"])


def _wind_at(t_ms: float, wind: list[dict[str, float]]) -> float | None:
    if not wind:
        return None
    nearest = min(wind, key=lambda w: abs(w["t"] - t_ms))
    if abs(nearest["t"] - t_ms) > 10 * 60 * 1000:
        return None
    return nearest["v"]


def _wind_cooling_insight(
    temp: list[dict[str, float]],
    wind: list[dict[str, float]],
) -> str | None:
    if len(temp) < 4 or len(wind) < 4:
        return None
    windy_temps: list[float] = []
    calm_temps: list[float] = []
    for pt in temp:
        w = _wind_at(pt["t"], wind)
        if w is None:
            continue
        if w >= 4.0:
            windy_temps.append(pt["v"])
        elif w <= 2.0:
            calm_temps.append(pt["v"])
    if len(windy_temps) < 2 or len(calm_temps) < 2:
        return None
    delta = (sum(calm_temps) / len(calm_temps)) - (sum(windy_temps) / len(windy_temps))
    if delta < 3.0:
        return None
    return f"Wind cooling: panels ~{delta:.0f}°C cooler when wind > 4 m/s"


def _cloud_flush_insight(
    temp: list[dict[str, float]],
    pv: list[dict[str, float]],
    *,
    ac_limit_kw: float,
) -> str | None:
    if len(temp) < 3 or len(pv) < 3 or ac_limit_kw <= 0:
        return None
    min_temp_pt = min(temp, key=lambda p: p["v"])
    min_temp = min_temp_pt["v"]
    min_t = min_temp_pt["t"]
    window_end = min_t + 90 * 60 * 1000
    peaks = [p for p in pv if min_t <= p["t"] <= window_end]
    if not peaks:
        return None
    peak_after = max(peaks, key=lambda p: p["v"])
    if peak_after["v"] < ac_limit_kw * CLIPPING_THRESHOLD:
        return None
    temps_after = [p["v"] for p in temp if min_t <= p["t"] <= window_end]
    if not temps_after or min(temps_after) > min_temp + 6:
        return None
    return (
        f"Cloud-edge flush: cold panels ({min_temp:.0f}°C) then peak "
        f"{peak_after['v']:.1f} kW within 90 min"
    )


def _clipping_insight(clipping_kw: list[dict[str, float]], *, ac_limit_kw: float) -> str | None:
    active = sum(1 for p in clipping_kw if p["v"] >= 0.02)
    minutes = active * BUCKET_MINUTES
    if minutes < 15:
        return None
    return f"Inverter clipping ~{minutes / 60.0:.1f} h at {ac_limit_kw:.1f} kW AC limit"


def build_intraday_physics_insights(
    series: dict[str, list[dict[str, Any]]],
    *,
    ac_limit_kw: float,
) -> list[str]:
    """Return human-readable physics insights for a performance day chart."""
    temp = _sorted_points(series.get("virtual_panel_temp_c"))
    wind = _sorted_points(series.get("wind_speed_ms"))
    pv = _sorted_points(series.get("pv_power_kw"))
    clip = _sorted_points(series.get("clipping_loss_kw"))

    insights: list[str] = []
    for note in (
        _wind_cooling_insight(temp, wind),
        _cloud_flush_insight(temp, pv, ac_limit_kw=ac_limit_kw),
        _clipping_insight(clip, ac_limit_kw=ac_limit_kw),
    ):
        if note:
            insights.append(note)
    return insights
