"""Octopus Energy Analysis — consumption, price/carbon merge, greener compliance."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .octopus_api import OctopusApiClient, OctopusApiError
from .octopus_consumption_store import OctopusConsumptionStore
from .octopus_greener import (
    GREEN_THRESHOLD_GCO2,
    is_low_carbon_green,
    low_carbon_score_from_gco2,
    normalize_carbon_periods,
)
from .octopus_tariff import (
    _parse_api_dt,
    _rate_value_inc_vat,
    is_variable_tariff_type,
    product_code_from_tariff_code,
    resolve_meter_for_consumption,
)

_LOGGER = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")

GREENER_NIGHT_START = time(23, 0)
GREENER_NIGHT_END = time(6, 0)

METER_COST_DAYS = 14
METER_COST_RATES_MAX_AGE = timedelta(hours=6)

COMPLIANCE_TIERS = (
    (90, 2800, "90%"),
    (80, 640, "80%"),
    (70, 320, "70%"),
)


def _iso_period(dt: datetime) -> str:
    return dt_util.as_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_consumption_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize Octopus half-hourly electricity consumption readings."""
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        start = _parse_api_dt(row.get("interval_start"))
        end = _parse_api_dt(row.get("interval_end"))
        if start is None:
            continue
        if end is None:
            end = start + timedelta(minutes=30)
        try:
            kwh = float(row.get("consumption"))
        except (TypeError, ValueError):
            continue
        start_local = start.astimezone(UK_TZ)
        out.append(
            {
                "start": start_local.isoformat(),
                "end": end.astimezone(UK_TZ).isoformat(),
                "start_ms": int(start.timestamp() * 1000),
                "end_ms": int(end.timestamp() * 1000),
                "kwh": round(kwh, 4),
            }
        )
    out.sort(key=lambda item: item["start_ms"])
    return out


def normalize_rate_periods(rates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chart-friendly import/export unit rate windows (p/kWh inc VAT)."""
    out: list[dict[str, Any]] = []
    for row in rates:
        if not isinstance(row, dict):
            continue
        start = _parse_api_dt(row.get("valid_from"))
        end = _parse_api_dt(row.get("valid_to"))
        if start is None:
            continue
        rate = _rate_value_inc_vat(row)
        if rate is None:
            continue
        out.append(
            {
                "start_ms": int(start.timestamp() * 1000),
                "end_ms": int(end.timestamp() * 1000) if end else None,
                "p_per_kwh": round(rate, 4),
            }
        )
    out.sort(key=lambda item: item["start_ms"])
    return out


def expand_rates_to_half_hours(
    rate_periods: list[dict[str, Any]],
    *,
    now_ms: int,
    slots: int = 48,
) -> list[dict[str, Any]]:
    """Expand rate windows into half-hour slots for charting."""
    if not rate_periods:
        return []
    slot_ms = 30 * 60 * 1000
    anchor = now_ms - (now_ms % slot_ms)
    start_ms = anchor - slot_ms
    out: list[dict[str, Any]] = []
    for i in range(slots):
        slot_start = start_ms + i * slot_ms
        slot_end = slot_start + slot_ms
        rate = None
        for period in rate_periods:
            end_ms = period.get("end_ms")
            if period["start_ms"] <= slot_start and (end_ms is None or slot_start < end_ms):
                rate = period.get("p_per_kwh")
                break
        out.append(
            {
                "start_ms": slot_start,
                "end_ms": slot_end,
                "p_per_kwh": rate,
            }
        )
    return out


def rate_p_at_ms(start_ms: int, rate_periods: list[dict[str, Any]]) -> float | None:
    """Return p/kWh for the rate window containing ``start_ms``."""
    try:
        when = int(start_ms)
    except (TypeError, ValueError):
        return None
    for period in rate_periods or []:
        try:
            period_start = int(period["start_ms"])
        except (KeyError, TypeError, ValueError):
            continue
        end_raw = period.get("end_ms")
        try:
            period_end = int(end_raw) if end_raw is not None else None
        except (TypeError, ValueError):
            period_end = None
        if period_start <= when and (period_end is None or when < period_end):
            try:
                return float(period["p_per_kwh"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def _uk_date_key(start_ms: int) -> str | None:
    try:
        local = datetime.fromtimestamp(int(start_ms) / 1000.0, tz=UK_TZ)
    except (TypeError, ValueError, OSError, OverflowError):
        return None
    return local.date().isoformat()


def compute_daily_meter_costs(
    import_rows: list[dict[str, Any]],
    export_rows: list[dict[str, Any]],
    import_rate_periods: list[dict[str, Any]],
    export_rate_periods: list[dict[str, Any]],
    *,
    days: int = METER_COST_DAYS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Join half-hourly meter kWh with unit rates → daily import spend / export earnings."""
    now = now or dt_util.now(UK_TZ)
    cutoff = now - timedelta(days=max(1, int(days)))
    cutoff_ms = int(cutoff.timestamp() * 1000)

    buckets: dict[str, dict[str, float]] = {}

    def _bucket(date_key: str) -> dict[str, float]:
        if date_key not in buckets:
            buckets[date_key] = {
                "import_spend_gbp": 0.0,
                "export_earnings_gbp": 0.0,
                "import_kwh": 0.0,
                "export_kwh": 0.0,
            }
        return buckets[date_key]

    priced_import = unpriced_import = 0
    priced_export = unpriced_export = 0

    for row in import_rows or []:
        try:
            start_ms = int(row.get("start_ms") or 0)
            kwh = float(row.get("kwh") or 0)
        except (TypeError, ValueError):
            continue
        if start_ms < cutoff_ms or kwh <= 0:
            continue
        date_key = _uk_date_key(start_ms)
        if not date_key:
            continue
        rate = rate_p_at_ms(start_ms, import_rate_periods)
        bucket = _bucket(date_key)
        bucket["import_kwh"] += kwh
        if rate is None:
            unpriced_import += 1
            continue
        priced_import += 1
        bucket["import_spend_gbp"] += kwh * rate / 100.0

    for row in export_rows or []:
        try:
            start_ms = int(row.get("start_ms") or 0)
            kwh = float(row.get("kwh") or 0)
        except (TypeError, ValueError):
            continue
        if start_ms < cutoff_ms or kwh <= 0:
            continue
        date_key = _uk_date_key(start_ms)
        if not date_key:
            continue
        rate = rate_p_at_ms(start_ms, export_rate_periods)
        bucket = _bucket(date_key)
        bucket["export_kwh"] += kwh
        if rate is None:
            unpriced_export += 1
            continue
        priced_export += 1
        bucket["export_earnings_gbp"] += kwh * rate / 100.0

    day_rows: list[dict[str, Any]] = []
    for date_key in sorted(buckets.keys())[-max(1, int(days)) :]:
        b = buckets[date_key]
        spend = round(b["import_spend_gbp"], 4)
        earn = round(b["export_earnings_gbp"], 4)
        day_rows.append(
            {
                "date": date_key,
                "import_spend_gbp": spend,
                "export_earnings_gbp": earn,
                "import_kwh": round(b["import_kwh"], 3),
                "export_kwh": round(b["export_kwh"], 3),
                "net_gbp": round(earn - spend, 4),
            }
        )

    total_spend = round(sum(d["import_spend_gbp"] for d in day_rows), 4)
    total_earn = round(sum(d["export_earnings_gbp"] for d in day_rows), 4)
    return {
        "days": day_rows,
        "totals": {
            "import_spend_gbp": total_spend,
            "export_earnings_gbp": total_earn,
            "net_gbp": round(total_earn - total_spend, 4),
            "import_kwh": round(sum(d["import_kwh"] for d in day_rows), 3),
            "export_kwh": round(sum(d["export_kwh"] for d in day_rows), 3),
        },
        "priced_import_intervals": priced_import,
        "unpriced_import_intervals": unpriced_import,
        "priced_export_intervals": priced_export,
        "unpriced_export_intervals": unpriced_export,
        "days_window": max(1, int(days)),
    }


def _resolve_product_code(octopus_cache: dict[str, Any], *, export: bool = False) -> str | None:
    prefix = "export" if export else "import"
    code = str(octopus_cache.get(f"{prefix}_product_code") or "").strip() or None
    if code:
        return code
    meter = octopus_cache.get(f"{prefix}_meter") or {}
    if isinstance(meter, dict):
        code = str(meter.get("product_code") or "").strip() or None
        if code:
            return code
        tariff = str(meter.get("tariff_code") or "").strip()
        if tariff:
            return product_code_from_tariff_code(tariff)
    tariff = str(octopus_cache.get(f"{prefix}_tariff_code") or "").strip()
    return product_code_from_tariff_code(tariff) if tariff else None


def _resolve_tariff_code(octopus_cache: dict[str, Any], *, export: bool = False) -> str | None:
    prefix = "export" if export else "import"
    code = str(octopus_cache.get(f"{prefix}_tariff_code") or "").strip() or None
    if code:
        return code
    meter = octopus_cache.get(f"{prefix}_meter") or {}
    if isinstance(meter, dict):
        return str(meter.get("tariff_code") or "").strip() or None
    return None


def _costs_cache_fresh(consumption_data: dict[str, Any] | None, *, now: datetime) -> bool:
    if not isinstance(consumption_data, dict):
        return False
    if not isinstance(consumption_data.get("daily_costs"), dict):
        return False
    raw = consumption_data.get("daily_costs_fetched_at")
    if not raw:
        return False
    try:
        fetched = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=dt_util.UTC)
    return (now.astimezone(dt_util.UTC) - fetched.astimezone(dt_util.UTC)) < METER_COST_RATES_MAX_AGE


async def fetch_historical_rate_periods(
    client: OctopusApiClient,
    *,
    product_code: str,
    tariff_code: str,
    days: int = METER_COST_DAYS,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Fetch unit-rate windows covering the last ``days`` (bill rates at use time)."""
    now = now or dt_util.utcnow()
    local_now = dt_util.as_local(now)
    period_from = _iso_period((local_now - timedelta(days=max(1, int(days)))).astimezone(dt_util.UTC))
    period_to = _iso_period((local_now + timedelta(hours=1)).astimezone(dt_util.UTC))
    rows = await client.get_unit_rates(
        product_code,
        tariff_code,
        period_from=period_from,
        period_to=period_to,
    )
    return normalize_rate_periods(rows)


async def refresh_meter_daily_costs(
    hass: Any,
    *,
    api_key: str,
    octopus_cache: dict[str, Any],
    consumption_data: dict[str, Any],
    days: int = METER_COST_DAYS,
    force: bool = False,
) -> dict[str, Any] | None:
    """Fetch historical unit rates and compute daily spend/earnings; cache on consumption_data."""
    now = dt_util.utcnow()
    if not force and _costs_cache_fresh(consumption_data, now=now):
        return consumption_data.get("daily_costs")

    import_rows = list(consumption_data.get("import") or [])
    export_rows = list(consumption_data.get("export") or [])
    if not import_rows and not export_rows:
        return None

    import_product = _resolve_product_code(octopus_cache, export=False)
    import_tariff = _resolve_tariff_code(octopus_cache, export=False)
    export_product = _resolve_product_code(octopus_cache, export=True)
    export_tariff = _resolve_tariff_code(octopus_cache, export=True)

    client = OctopusApiClient(hass, api_key=api_key)
    import_periods: list[dict[str, Any]] = []
    export_periods: list[dict[str, Any]] = []
    errors: dict[str, str] = {}

    if import_product and import_tariff:
        try:
            import_periods = await fetch_historical_rate_periods(
                client,
                product_code=import_product,
                tariff_code=import_tariff,
                days=days,
                now=now,
            )
        except OctopusApiError as err:
            errors["import_cost_rates"] = str(err)
            _LOGGER.warning("Octopus historical import rates failed: %s", err)
    else:
        errors["import_cost_rates"] = "Import tariff/product required for spend chart"

    if export_product and export_tariff:
        try:
            export_periods = await fetch_historical_rate_periods(
                client,
                product_code=export_product,
                tariff_code=export_tariff,
                days=days,
                now=now,
            )
        except OctopusApiError as err:
            errors["export_cost_rates"] = str(err)
            _LOGGER.warning("Octopus historical export rates failed: %s", err)

    if not import_periods and not export_periods:
        if errors:
            consumption_data.setdefault("errors", {}).update(errors)
        return None

    costs = compute_daily_meter_costs(
        import_rows,
        export_rows,
        import_periods,
        export_periods,
        days=days,
        now=dt_util.now(UK_TZ),
    )
    costs["fetched_at"] = now.isoformat()
    if errors:
        costs["errors"] = errors
        consumption_data.setdefault("errors", {}).update(errors)
    consumption_data["daily_costs"] = costs
    consumption_data["daily_costs_fetched_at"] = now.isoformat()
    return costs


def carbon_extremes(periods: list[dict[str, Any]], *, now_ms: int | None = None) -> dict[str, Any]:
    """Best and worst half-hours in the next 24h carbon forecast."""
    now_ms = now_ms if now_ms is not None else int(dt_util.now(UK_TZ).timestamp() * 1000)
    horizon = now_ms + 24 * 60 * 60 * 1000
    future = [
        p
        for p in periods
        if p.get("start_ms", 0) >= now_ms
        and p.get("start_ms", 0) < horizon
        and p.get("gco2_per_kwh") is not None
    ]
    if not future:
        return {}
    worst = max(future, key=lambda p: float(p["gco2_per_kwh"]))
    best = min(future, key=lambda p: float(p["gco2_per_kwh"]))
    return {
        "worst_gco2": worst.get("gco2_per_kwh"),
        "worst_start_ms": worst.get("start_ms"),
        "best_gco2": best.get("gco2_per_kwh"),
        "best_start_ms": best.get("start_ms"),
    }


def _carbon_period_for_slot(
    start_ms: int | float | None,
    carbon_periods: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the carbon half-hour that contains slot start (interval match, not exact key)."""
    if start_ms is None or not carbon_periods:
        return None
    try:
        when_ms = int(start_ms)
    except (TypeError, ValueError):
        return None
    for row in carbon_periods:
        raw_start = row.get("start_ms")
        raw_end = row.get("end_ms")
        if raw_start is None:
            continue
        try:
            period_start = int(raw_start)
            period_end = int(raw_end) if raw_end is not None else period_start + 30 * 60 * 1000
        except (TypeError, ValueError):
            continue
        if period_start <= when_ms < period_end:
            return row
    return None


def merge_price_and_carbon(
    rate_slots: list[dict[str, Any]],
    carbon_periods: list[dict[str, Any]],
    export_slots: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Align half-hour import/export rates with carbon intensity for dual-axis charts."""
    export_by_start = {
        int(p["start_ms"]): p
        for p in (export_slots or [])
        if p.get("start_ms") is not None
    }
    merged: list[dict[str, Any]] = []
    for slot in rate_slots:
        start_ms = slot.get("start_ms")
        carbon = _carbon_period_for_slot(start_ms, carbon_periods)
        export_slot = None
        if start_ms is not None:
            try:
                export_slot = export_by_start.get(int(start_ms))
            except (TypeError, ValueError):
                export_slot = None
        gco2 = carbon.get("gco2_per_kwh") if carbon else None
        score = carbon.get("low_carbon_score") if carbon else None
        if score is None and gco2 is not None:
            score = low_carbon_score_from_gco2(gco2)
        merged.append(
            {
                "start_ms": start_ms,
                "end_ms": slot.get("end_ms"),
                "p_per_kwh": slot.get("p_per_kwh"),
                "export_p_per_kwh": export_slot.get("p_per_kwh") if export_slot else None,
                "gco2_per_kwh": gco2,
                "low_carbon_score": score,
                "is_green": is_low_carbon_green(gco2=gco2, score=score),
            }
        )
    return merged


def _greener_night_window(night_date: str) -> tuple[datetime, datetime] | None:
    try:
        day = date.fromisoformat(str(night_date))
    except ValueError:
        return None
    start = datetime.combine(day - timedelta(days=1), GREENER_NIGHT_START, tzinfo=UK_TZ)
    end = datetime.combine(day, GREENER_NIGHT_END, tzinfo=UK_TZ)
    return start, end


def _interval_overlaps(start_ms: int, end_ms: int, win_start: datetime, win_end: datetime) -> bool:
    ws = int(win_start.timestamp() * 1000)
    we = int(win_end.timestamp() * 1000)
    return start_ms < we and end_ms > ws


def _is_overnight_window(start_ms: int, end_ms: int) -> bool:
    start = datetime.fromtimestamp(start_ms / 1000, tz=UK_TZ)
    end = datetime.fromtimestamp(end_ms / 1000, tz=UK_TZ)
    t = start.time()
    if t >= GREENER_NIGHT_START:
        return True
    return t < GREENER_NIGHT_END


def compute_greener_compliance(
    consumption: list[dict[str, Any]],
    greener_nights: list[dict[str, Any]],
    *,
    month: date | None = None,
) -> dict[str, Any]:
    """Estimate greener-night alignment from smart-meter import (23:00–06:00)."""
    month = month or dt_util.now(UK_TZ).date().replace(day=1)
    if month.day != 1:
        month = month.replace(day=1)
    next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_start_ms = int(datetime.combine(month, time.min, tzinfo=UK_TZ).timestamp() * 1000)
    month_end_ms = int(datetime.combine(next_month, time.min, tzinfo=UK_TZ).timestamp() * 1000)

    greener_windows: list[tuple[str, datetime, datetime]] = []
    for row in greener_nights:
        if not row.get("is_greener_night"):
            continue
        window = _greener_night_window(str(row.get("date")))
        if window:
            greener_windows.append((str(row.get("date")), window[0], window[1]))

    overnight_kwh = 0.0
    greener_kwh = 0.0
    for row in consumption:
        start_ms = row.get("start_ms")
        end_ms = row.get("end_ms")
        if start_ms is None or end_ms is None:
            continue
        if end_ms <= month_start_ms or start_ms >= month_end_ms:
            continue
        kwh = float(row.get("kwh") or 0)
        if not _is_overnight_window(start_ms, end_ms):
            continue
        overnight_kwh += kwh
        for _, win_start, win_end in greener_windows:
            if win_start.timestamp() * 1000 >= month_end_ms:
                break
            if win_end.timestamp() * 1000 <= month_start_ms:
                continue
            if _interval_overlaps(start_ms, end_ms, win_start, win_end):
                greener_kwh += kwh
                break

    pct = round(greener_kwh / overnight_kwh * 100, 1) if overnight_kwh > 0.01 else None
    next_tier = None
    projected_points = 0
    if pct is not None:
        for threshold, points, label in COMPLIANCE_TIERS:
            if pct >= threshold:
                projected_points = points
                break
            next_tier = {"threshold_pct": threshold, "points": points, "label": label}
    return {
        "month": month.isoformat(),
        "overnight_kwh": round(overnight_kwh, 2),
        "greener_overnight_kwh": round(greener_kwh, 2),
        "alignment_pct": pct,
        "projected_octopoints": projected_points if pct is not None else None,
        "next_tier": next_tier,
        "greener_nights_count": len(greener_windows),
        "note": (
            "Based on smart-meter import during 11pm–6am vs nights flagged greener. "
            "Intelligent Octopus Go rewards use connected EV charging data from Octopus."
        ),
    }


def build_greener_history_insights(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive wasGreenerNight flags and forecast flips from stored snapshots."""
    was_greener: dict[str, bool] = {}
    flips: list[dict[str, str]] = []
    last_flag: dict[str, bool | None] = {}

    for entry in history:
        if not isinstance(entry, dict):
            continue
        snap = entry.get("snapshot")
        if not isinstance(snap, dict):
            continue
        recorded_at = str(entry.get("recorded_at") or "")
        for row in snap.get("greener_nights") or []:
            if not isinstance(row, dict):
                continue
            day = str(row.get("date") or "")
            if not day:
                continue
            flagged = bool(row.get("is_greener_night"))
            was_greener[day] = was_greener.get(day, False) or flagged
            prev = last_flag.get(day)
            if prev is not None and prev != flagged:
                flips.append(
                    {
                        "date": day,
                        "recorded_at": recorded_at,
                        "from": "greener" if prev else "not greener",
                        "to": "greener" if flagged else "not greener",
                    }
                )
            last_flag[day] = flagged

    flip_rows = sorted(flips, key=lambda r: r.get("recorded_at") or "", reverse=True)[:8]
    return {
        "was_greener_by_date": was_greener,
        "forecast_flips": flip_rows,
        "snapshot_count": len(history),
    }


def enrich_greener_nights_with_history(
    greener_nights: list[dict[str, Any]],
    was_greener_by_date: dict[str, bool],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in greener_nights:
        day = str(row.get("date") or "")
        copy = dict(row)
        copy["was_greener_night"] = bool(was_greener_by_date.get(day, False))
        copy["forecast_changed"] = (
            copy["was_greener_night"] and not copy.get("is_greener_night")
        ) or (
            not copy["was_greener_night"] and copy.get("is_greener_night")
        )
        out.append(copy)
    return out


async def fetch_meter_consumption(
    client: OctopusApiClient,
    *,
    mpan: str,
    serial: str,
    days: int = 35,
) -> list[dict[str, Any]]:
    if not mpan or not serial:
        return []
    local_now = dt_util.as_local(dt_util.utcnow())
    period_from = _iso_period((local_now - timedelta(days=days)).astimezone(dt_util.UTC))
    period_to = _iso_period(local_now.astimezone(dt_util.UTC))
    rows = await client.get_electricity_consumption(
        mpan,
        serial,
        period_from=period_from,
        period_to=period_to,
    )
    return normalize_consumption_rows(rows)


async def refresh_octopus_consumption(
    hass: Any,
    store: Any,
    *,
    api_key: str,
    octopus_cache: dict[str, Any],
    greener_cache: dict[str, Any],
    greener_nights: list[dict[str, Any]] | None = None,
    import_days: int = 3,
    export_days: int = 3,
) -> dict[str, Any]:
    """Fetch recent meter readings, merge into store, return stored rows + compliance."""
    result: dict[str, Any] = {
        "import": [],
        "export": [],
        "compliance": None,
        "last_fetch_at": None,
        "errors": {},
        "daily_costs": None,
        "daily_costs_fetched_at": None,
    }
    import_meter = octopus_cache.get("import_meter") or greener_cache.get("import_meter") or {}
    export_meter = resolve_meter_for_consumption(octopus_cache, export=True)
    if not (export_meter.get("mpan") and export_meter.get("serial")):
        greener_export = greener_cache.get("export_meter") if isinstance(greener_cache.get("export_meter"), dict) else {}
        if greener_export.get("mpan") and greener_export.get("serial"):
            export_meter = greener_export
        elif not export_meter.get("mpan") and greener_export:
            export_meter = greener_export
    # Prefer fully resolved import meter (mpan+serial) from cache lists when singular is incomplete.
    resolved_import = resolve_meter_for_consumption(octopus_cache, export=False)
    if resolved_import.get("mpan") and resolved_import.get("serial"):
        import_meter = resolved_import
    mpan = str(import_meter.get("mpan") or "").strip()
    serial = str(import_meter.get("serial") or "").strip()
    client = OctopusApiClient(hass, api_key=api_key)
    import_rows: list[dict[str, Any]] | None = None
    export_rows: list[dict[str, Any]] | None = None

    if mpan and serial:
        try:
            import_rows = await fetch_meter_consumption(
                client, mpan=mpan, serial=serial, days=import_days
            )
        except OctopusApiError as err:
            result["errors"]["consumption"] = str(err)
            _LOGGER.warning("Octopus import consumption fetch failed: %s", err)
    else:
        result["errors"]["consumption"] = (
            "Import meter MPAN and serial required — connect Octopus with a valid account"
        )

    exp_mpan = str(export_meter.get("mpan") or "").strip()
    exp_serial = str(export_meter.get("serial") or "").strip()
    if exp_mpan and exp_serial:
        try:
            export_rows = await fetch_meter_consumption(
                client, mpan=exp_mpan, serial=exp_serial, days=export_days
            )
        except OctopusApiError as err:
            result["errors"]["export_consumption"] = str(err)
            _LOGGER.warning("Octopus export consumption fetch failed: %s", err)
    elif exp_mpan and not exp_serial:
        result["errors"]["export_consumption"] = (
            f"Export MPAN {exp_mpan[-4:]} found but meter serial is missing — "
            "re-test Octopus connection so GraphQL can fill the serial"
        )
        _LOGGER.warning("Octopus export consumption skipped: MPAN without serial")
    elif octopus_cache.get("export_tariff_code") or octopus_cache.get("export_rates"):
        result["errors"]["export_consumption"] = (
            "Export tariff is linked but no export meter serial is available for smart-meter polling"
        )
    elif octopus_cache.get("export_meters"):
        result["errors"]["export_consumption"] = (
            "Export meter listed on the account but MPAN/serial incomplete — re-test Octopus connection"
        )

    if exp_mpan and exp_serial and export_rows is not None and not export_rows:
        # API succeeded but Octopus has not published half-hours yet (often batched ~daily).
        result["errors"]["export_consumption"] = (
            "Export meter polled OK but Octopus returned no half-hourly readings yet "
            "(export data often arrives in a daily batch) — falling back to Glow/Fox when available"
        )

    if import_rows or export_rows:
        stored = await store.async_merge_rows(
            import_rows=import_rows,
            export_rows=export_rows,
            fetched_at=dt_util.utcnow().isoformat(),
        )
    else:
        stored = await store.async_load()

    nights = greener_nights if greener_nights is not None else list(greener_cache.get("greener_nights") or [])
    import_data = list(stored.get("import") or [])
    result["import"] = import_data
    result["export"] = list(stored.get("export") or [])
    result["last_fetch_at"] = stored.get("last_fetch_at")
    if import_data:
        result["compliance"] = compute_greener_compliance(import_data, nights)

    try:
        await refresh_meter_daily_costs(
            hass,
            api_key=api_key,
            octopus_cache=octopus_cache,
            consumption_data=result,
            days=METER_COST_DAYS,
            force=True,
        )
    except Exception as err:  # noqa: BLE001 — keep meter poll success even if cost join fails
        _LOGGER.warning("Octopus meter cost refresh failed: %s", err)
        result["errors"]["meter_costs"] = str(err)

    return result


async def apply_hybrid_export_to_consumption(
    hass: Any,
    consumption_data: dict[str, Any],
    *,
    glow_export_cumulative_entity_id: str | None = None,
    fox_export_today_entity_id: str | None = None,
    days: int = METER_COST_DAYS,
) -> dict[str, Any]:
    """Overlay export half-hours from Octopus → Glow → Fox for charts and £ join."""
    from .export_energy_hybrid import async_resolve_hybrid_export_rows

    hybrid_rows, source, note = await async_resolve_hybrid_export_rows(
        hass,
        octopus_export_rows=list(consumption_data.get("export") or []),
        glow_export_cumulative_entity_id=glow_export_cumulative_entity_id,
        fox_export_today_entity_id=fox_export_today_entity_id,
        days=days,
    )
    consumption_data["export_kwh_source"] = source
    consumption_data["export_hybrid_note"] = note
    if source and source != "octopus" and hybrid_rows:
        consumption_data["export_display"] = hybrid_rows
    else:
        consumption_data["export_display"] = list(consumption_data.get("export") or [])
    if note and source != "octopus":
        # Soft hint — keep prior hard errors, don't mask serial/API failures.
        consumption_data.setdefault("errors", {}).setdefault("export_hybrid", note)
    return consumption_data


async def build_octopus_analysis_snapshot(
    hass: Any,
    *,
    api_key: str | None,
    octopus_cache: dict[str, Any],
    greener_cache: dict[str, Any],
    greener_history: list[dict[str, Any]],
    consumption_data: dict[str, Any] | None = None,
    glow_export_cumulative_entity_id: str | None = None,
    fox_export_today_entity_id: str | None = None,
) -> dict[str, Any]:
    """Build the Octopus Energy Analysis payload for the panel."""
    now = dt_util.now(UK_TZ)
    now_ms = int(now.timestamp() * 1000)
    carbon_periods = list(greener_cache.get("carbon_periods") or [])
    greener_nights = list(greener_cache.get("greener_nights") or [])
    history_insights = build_greener_history_insights(greener_history)
    enriched_nights = enrich_greener_nights_with_history(
        greener_nights,
        history_insights.get("was_greener_by_date") or {},
    )

    import_rates = normalize_rate_periods(octopus_cache.get("import_rates") or [])
    export_rates = normalize_rate_periods(octopus_cache.get("export_rates") or [])
    import_slots = expand_rates_to_half_hours(import_rates, now_ms=now_ms)
    export_slots = expand_rates_to_half_hours(export_rates, now_ms=now_ms) if export_rates else []
    dual_periods = merge_price_and_carbon(import_slots, carbon_periods, export_slots)

    snapshot: dict[str, Any] = {
        "fetched_at": dt_util.utcnow().isoformat(),
        "tariff_type": octopus_cache.get("tariff_type"),
        "import_tariff_code": octopus_cache.get("import_tariff_code"),
        "export_tariff_code": octopus_cache.get("export_tariff_code"),
        "current_import_p_per_kwh": octopus_cache.get("current_import_p_per_kwh"),
        "current_export_p_per_kwh": octopus_cache.get("current_export_p_per_kwh"),
        "import_standing_p_per_day": octopus_cache.get("import_standing_p_per_day"),
        "carbon_extremes": carbon_extremes(carbon_periods, now_ms=now_ms),
        "import_rate_slots": import_slots,
        "export_rate_slots": export_slots,
        "dual_periods": dual_periods,
        "greener_nights": enriched_nights,
        "history": history_insights,
        "consumption": [],
        "export_consumption": [],
        "export_kwh_source": None,
        "export_hybrid_note": None,
        "daily_costs": None,
        "compliance": None,
        "consumption_fetched_at": None,
        "errors": {},
    }

    cons = consumption_data if isinstance(consumption_data, dict) else {}
    if cons:
        try:
            await apply_hybrid_export_to_consumption(
                hass,
                cons,
                glow_export_cumulative_entity_id=glow_export_cumulative_entity_id,
                fox_export_today_entity_id=fox_export_today_entity_id,
                days=METER_COST_DAYS,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Hybrid export resolve failed: %s", err)
            cons.setdefault("errors", {})["export_hybrid"] = str(err)

    snapshot["consumption"] = list(cons.get("import") or [])
    snapshot["export_consumption"] = list(
        cons.get("export_display") or cons.get("export") or []
    )
    snapshot["export_kwh_source"] = cons.get("export_kwh_source")
    snapshot["export_hybrid_note"] = cons.get("export_hybrid_note")
    snapshot["compliance"] = cons.get("compliance")
    snapshot["consumption_fetched_at"] = cons.get("last_fetch_at")
    if cons.get("errors"):
        snapshot["errors"].update(cons["errors"])

    if not api_key:
        snapshot["errors"]["auth"] = "Octopus API key required for live rates and meter polling"
        snapshot["daily_costs"] = cons.get("daily_costs")
        return snapshot

    if not snapshot["consumption"] and not snapshot["errors"].get("consumption"):
        snapshot["errors"]["consumption"] = (
            "Smart-meter consumption will populate after the next half-hourly Octopus poll"
        )

    # Re-run cost join against display export rows (hybrid may replace empty Octopus export).
    if cons and (cons.get("import") or cons.get("export_display") or cons.get("export")):
        cost_input = dict(cons)
        cost_input["export"] = list(cons.get("export_display") or cons.get("export") or [])
        try:
            costs = await refresh_meter_daily_costs(
                hass,
                api_key=api_key,
                octopus_cache=octopus_cache,
                consumption_data=cost_input,
                days=METER_COST_DAYS,
                force=True,
            )
            snapshot["daily_costs"] = costs or cost_input.get("daily_costs")
            if costs:
                costs["export_kwh_source"] = cons.get("export_kwh_source")
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Octopus meter cost join failed: %s", err)
            snapshot["daily_costs"] = cons.get("daily_costs")
            snapshot["errors"]["meter_costs"] = str(err)
    else:
        snapshot["daily_costs"] = cons.get("daily_costs")

    return snapshot


def octopus_consumption_sensor_values(
    import_rows: list[dict[str, Any]],
    compliance: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, float | None]:
    """Values for recorder-friendly Octopus consumption sensors."""
    now = now or dt_util.now(UK_TZ)
    today = now.date()
    today_start = int(datetime.combine(today, time.min, tzinfo=UK_TZ).timestamp() * 1000)
    today_kwh = sum(
        float(r.get("kwh") or 0)
        for r in import_rows
        if int(r.get("start_ms") or 0) >= today_start
    )
    latest = OctopusConsumptionStore.latest_row(import_rows) if import_rows else None
    half_hour = float(latest["kwh"]) if latest and latest.get("kwh") is not None else None
    alignment = compliance.get("alignment_pct") if isinstance(compliance, dict) else None
    return {
        "half_hour_kwh": round(half_hour, 4) if half_hour is not None else None,
        "today_kwh": round(today_kwh, 3) if today_kwh else None,
        "greener_alignment_pct": float(alignment) if alignment is not None else None,
    }


def octopus_analysis_dashboard_payload(
    snapshot: dict[str, Any] | None,
    *,
    greener_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Panel-friendly merge of analysis snapshot + greener dashboard fields."""
    if not isinstance(snapshot, dict):
        return None
    greener = greener_payload if isinstance(greener_payload, dict) else {}
    carbon_periods = list(
        greener.get("carbon_periods") or snapshot.get("carbon_periods") or []
    )
    # Always rebuild overlay rows from the latest greener carbon forecast so the
    # price/carbon chart does not stay stuck at score 0 when carbon arrives later.
    dual_periods = merge_price_and_carbon(
        list(snapshot.get("import_rate_slots") or []),
        carbon_periods,
        list(snapshot.get("export_rate_slots") or []),
    )
    return {
        **snapshot,
        "greener_title": greener.get("title"),
        "carbon_periods": carbon_periods,
        "dual_periods": dual_periods or snapshot.get("dual_periods") or [],
        "timeline": greener.get("timeline") or [],
        "green_threshold_gco2": greener.get("green_threshold_gco2") or GREEN_THRESHOLD_GCO2,
        "rewards": greener.get("rewards"),
        "greener_history_count": greener.get("history_count"),
        "postcode": greener.get("postcode"),
        "carbon_source": greener.get("carbon_source") or snapshot.get("carbon_source"),
        "errors": {**(greener.get("errors") or {}), **(snapshot.get("errors") or {})},
        "variable_tariff": is_variable_tariff_type(str(snapshot.get("tariff_type") or "")),
    }
