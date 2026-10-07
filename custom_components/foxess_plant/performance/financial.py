"""Per-bucket and daily financial calculations.

Savings are measured against the same house load bought entirely from the grid at the same rates:
  savings = load × import rate − (import × import rate − export × export rate)
          = avoided grid cost + export earnings, where avoided grid cost = (load − import) × import rate.
Avoided cost can be negative in a bucket where the battery charges from the grid; that's paid back
later when the battery covers the load.
"""

from __future__ import annotations

from typing import Any

BUCKET_HOURS = 5.0 / 60.0

# Daily kWh counters priced each tick: key in the accumulator → key in coordinator analytics
ENERGY_COUNTERS = {
    "import": "load_from_grid_kwh_today",
    "export": "pv_to_grid_kwh_today",
    "load": "load_consumption_kwh_today",
}


def bucket_financials_gbp(
    *,
    import_kwh: float,
    export_kwh: float,
    load_kwh: float,
    import_p_per_kwh: float,
    export_p_per_kwh: float,
) -> dict[str, float]:
    """Export earnings, import spend, avoided cost, and net saving for one bucket."""
    # Not clamped to >=0: a tick's delta can be negative when a counter dips (see counter_deltas), and the
    # daily sum must telescope to the true net rather than only counting up-moves.
    imp_kwh = float(import_kwh)
    exp_kwh = float(export_kwh)
    load = float(load_kwh)
    imp_p = float(import_p_per_kwh)
    exp_p = float(export_p_per_kwh)
    export_earnings = exp_kwh * exp_p / 100.0
    import_spend = imp_kwh * imp_p / 100.0
    avoided_cost = (load - imp_kwh) * imp_p / 100.0
    return {
        "export_earnings_gbp": round(export_earnings, 4),
        "import_spend_gbp": round(import_spend, 4),
        "avoided_grid_cost_gbp": round(avoided_cost, 4),
        "net_bucket_gbp": round(avoided_cost + export_earnings, 4),
    }


def counter_deltas(
    last: dict[str, float] | None, analytics: dict[str, Any]
) -> tuple[dict[str, float], dict[str, float]]:
    """kWh since the last tick from the daily counters, and the readings to remember.

    With no previous reading nothing is counted (we can't price energy from before we were running).
    A counter that goes down (meter source changed, or reset) is re-read without counting.
    """
    deltas: dict[str, float] = {}
    readings: dict[str, float] = dict(last or {})
    for key, source in ENERGY_COUNTERS.items():
        raw = analytics.get(source)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            deltas[key] = 0.0
            continue
        prev = (last or {}).get(key)
        if prev is None:
            deltas[key] = 0.0
        else:
            prev_f = float(prev)
            delta = value - prev_f
            # Treat ONLY a collapse to ~zero as a reset (midnight rollover / source change) — not a normal
            # intraday dip. load_consumption = base_load - discharge + charge + grid is a composite that
            # legitimately swings down a lot when the battery discharges; keeping those negative deltas lets
            # a day telescope to its true net. A ratio guard (value < prev/2) mis-fired on those swings and
            # re-inflated priced load → avoided-cost → savings several-fold (true 10.5 kWh counted as ~29).
            deltas[key] = 0.0 if (prev_f > 0.5 and value <= 0.05) else delta
        readings[key] = value
    return deltas, readings


def accumulate_bucket_financials(acc: dict[str, Any], bucket: dict[str, float]) -> None:
    """Add bucket financial lines into a daily accumulator dict."""
    for key in (
        "export_earnings_gbp",
        "import_spend_gbp",
        "avoided_grid_cost_gbp",
        "net_bucket_gbp",
        "import_kwh",
        "export_kwh",
        "clipping_loss_kwh",
        "clipping_loss_valuation_gbp",
    ):
        acc[key] = float(acc.get(key) or 0.0) + float(bucket.get(key) or 0.0)
    acc["peak_power_kw"] = max(float(acc.get("peak_power_kw") or 0.0), float(bucket.get("pv_power_kw") or 0.0))
    vtemp = bucket.get("virtual_panel_temp_c")
    if vtemp is not None:
        acc["virtual_temp_min_c"] = min(float(acc.get("virtual_temp_min_c") or vtemp), float(vtemp))
        acc["virtual_temp_max_c"] = max(float(acc.get("virtual_temp_max_c") or vtemp), float(vtemp))


def accumulate_weather_metrics(acc: dict[str, Any], sample: Any) -> None:
    """Track daily weather averages and precipitation sum for ledger analytics."""
    vis = getattr(sample, "visibility_km", None)
    if vis is not None:
        acc["visibility_sum_km"] = float(acc.get("visibility_sum_km") or 0.0) + float(vis)
        acc["visibility_count"] = int(acc.get("visibility_count") or 0) + 1
    dew = getattr(sample, "dew_point_c", None)
    if dew is not None:
        acc["dew_sum_c"] = float(acc.get("dew_sum_c") or 0.0) + float(dew)
        acc["dew_count"] = int(acc.get("dew_count") or 0) + 1
    precip = getattr(sample, "precipitation_mm", None)
    if precip is not None and float(precip) > 0:
        acc["precipitation_mm"] = float(acc.get("precipitation_mm") or 0.0) + float(precip)
    vtemp = getattr(sample, "virtual_panel_temp_c", None)
    if vtemp is not None and getattr(sample, "pv_power_kw", None) and float(sample.pv_power_kw) > 0.1:
        acc["virtual_temp_daylight_sum_c"] = float(acc.get("virtual_temp_daylight_sum_c") or 0.0) + float(
            vtemp
        )
        acc["virtual_temp_daylight_count"] = int(acc.get("virtual_temp_daylight_count") or 0) + 1


def estimate_bucket_energy_kwh(power_kw: float | None) -> float:
    if power_kw is None:
        return 0.0
    return max(0.0, float(power_kw)) * BUCKET_HOURS


def net_daily_savings_gbp(row: dict[str, Any]) -> float:
    return round(float(row.get("export_earnings_gbp") or 0) + float(row.get("avoided_grid_cost_gbp") or 0), 2)
