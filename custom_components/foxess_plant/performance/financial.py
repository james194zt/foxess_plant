"""Per-bucket and daily financial calculations."""

from __future__ import annotations

from typing import Any

BUCKET_HOURS = 5.0 / 60.0


def bucket_financials_gbp(
    *,
    import_kwh: float,
    export_kwh: float,
    load_kwh: float,
    import_p_per_kwh: float,
    export_p_per_kwh: float,
) -> dict[str, float]:
    """Compute export earnings, import spend, avoided cost, and net for one bucket."""
    imp_kwh = max(0.0, float(import_kwh))
    exp_kwh = max(0.0, float(export_kwh))
    load = max(0.0, float(load_kwh))
    imp_p = float(import_p_per_kwh)
    exp_p = float(export_p_per_kwh)
    self_consumed = max(0.0, load - imp_kwh)
    export_earnings = exp_kwh * exp_p / 100.0
    import_spend = imp_kwh * imp_p / 100.0
    avoided_cost = self_consumed * imp_p / 100.0
    net = export_earnings + avoided_cost - import_spend
    return {
        "export_earnings_gbp": round(export_earnings, 4),
        "import_spend_gbp": round(import_spend, 4),
        "avoided_grid_cost_gbp": round(avoided_cost, 4),
        "net_bucket_gbp": round(net, 4),
        "self_consumed_kwh": round(self_consumed, 4),
    }


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
    return round(
        float(row.get("export_earnings_gbp") or 0)
        + float(row.get("avoided_grid_cost_gbp") or 0)
        - float(row.get("import_spend_gbp") or 0),
        2,
    )
