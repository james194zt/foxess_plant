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


def _haze_insight(
    visibility: list[dict[str, float]],
    pv: list[dict[str, float]],
    solcast: list[dict[str, float]],
) -> str | None:
    if len(visibility) < 3:
        return None
    low_vis = [p for p in visibility if p["v"] < 8.0]
    if len(low_vis) < max(2, len(visibility) // 4):
        return None
    underperform = 0
    compared = 0
    for pt in low_vis:
        nearest_pv = min(pv, key=lambda p: abs(p["t"] - pt["t"])) if pv else None
        nearest_fc = min(solcast, key=lambda p: abs(p["t"] - pt["t"])) if solcast else None
        if not nearest_pv or not nearest_fc:
            continue
        if abs(nearest_pv["t"] - pt["t"]) > 15 * 60 * 1000:
            continue
        if nearest_fc["v"] <= 0.05:
            continue
        compared += 1
        if nearest_pv["v"] < nearest_fc["v"] * 0.85:
            underperform += 1
    if compared < 2 or underperform < 2:
        return None
    avg_vis = sum(p["v"] for p in low_vis) / len(low_vis)
    return f"Haze correlation: PV below forecast during visibility ~{avg_vis:.0f} km"


def _dew_insight(dew: list[dict[str, float]], temp: list[dict[str, float]]) -> str | None:
    if len(dew) < 3 or len(temp) < 3:
        return None
    high_dew = [p for p in dew if p["v"] >= 14.0]
    if len(high_dew) < 2:
        return None
    cold_mornings = 0
    for pt in high_dew:
        nearest = min(temp, key=lambda t: abs(t["t"] - pt["t"]))
        if abs(nearest["t"] - pt["t"]) > 15 * 60 * 1000:
            continue
        if nearest["v"] <= pt["v"] + 2.0:
            cold_mornings += 1
    if cold_mornings < 2:
        return None
    return "High dew point: panel condensation risk in early hours"


def _precip_insight(precip: list[dict[str, float]], visibility: list[dict[str, float]]) -> str | None:
    wet = [p for p in precip if p["v"] > 0.02]
    if len(wet) < 2:
        return None
    total = sum(p["v"] for p in wet)
    vis_after = [v for v in visibility if any(abs(v["t"] - w["t"]) < 60 * 60 * 1000 for w in wet)]
    clearer = [v for v in vis_after if v["v"] >= 12]
    if len(clearer) >= 2:
        return f"Rain event ~{total:.1f} mm then visibility improved — watch for yield recovery"
    return f"Rain ~{total:.1f} mm logged — soiling wash possible"


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
    visibility = _sorted_points(series.get("visibility_km"))
    dew = _sorted_points(series.get("dew_point_c"))
    precip = _sorted_points(series.get("precipitation_mm"))
    solcast = _sorted_points(series.get("solcast_forecast_kw"))

    insights: list[str] = []
    for note in (
        _wind_cooling_insight(temp, wind),
        _cloud_flush_insight(temp, pv, ac_limit_kw=ac_limit_kw),
        _clipping_insight(clip, ac_limit_kw=ac_limit_kw),
        _haze_insight(visibility, pv, solcast),
        _dew_insight(dew, temp),
        _precip_insight(precip, visibility),
    ):
        if note:
            insights.append(note)
    return insights
