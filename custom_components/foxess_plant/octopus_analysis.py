"""Octopus Energy Analysis — consumption, price/carbon merge, greener compliance."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .octopus_api import OctopusApiClient, OctopusApiError
from .octopus_consumption_store import OctopusConsumptionStore
from .octopus_greener import GREEN_THRESHOLD_GCO2, low_carbon_score_from_gco2, normalize_carbon_periods
from .octopus_tariff import _parse_api_dt, _rate_value_inc_vat, is_variable_tariff_type

_LOGGER = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")

GREENER_NIGHT_START = time(23, 0)
GREENER_NIGHT_END = time(6, 0)

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


def merge_price_and_carbon(
    rate_slots: list[dict[str, Any]],
    carbon_periods: list[dict[str, Any]],
    export_slots: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Align half-hour import/export rates with carbon intensity for dual-axis charts."""
    carbon_by_start = {p["start_ms"]: p for p in carbon_periods if p.get("start_ms") is not None}
    export_by_start = {
        p["start_ms"]: p for p in (export_slots or []) if p.get("start_ms") is not None
    }
    merged: list[dict[str, Any]] = []
    for slot in rate_slots:
        start_ms = slot.get("start_ms")
        carbon = carbon_by_start.get(start_ms) if start_ms is not None else None
        export_slot = export_by_start.get(start_ms) if start_ms is not None else None
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
                "is_green": gco2 is not None and float(gco2) < GREEN_THRESHOLD_GCO2,
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
    }
    import_meter = octopus_cache.get("import_meter") or greener_cache.get("import_meter") or {}
    export_meter = octopus_cache.get("export_meter") or greener_cache.get("export_meter") or {}
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
    return result


async def build_octopus_analysis_snapshot(
    hass: Any,
    *,
    api_key: str | None,
    octopus_cache: dict[str, Any],
    greener_cache: dict[str, Any],
    greener_history: list[dict[str, Any]],
    consumption_data: dict[str, Any] | None = None,
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
        "compliance": None,
        "consumption_fetched_at": None,
        "errors": {},
    }

    cons = consumption_data if isinstance(consumption_data, dict) else {}
    snapshot["consumption"] = list(cons.get("import") or [])
    snapshot["export_consumption"] = list(cons.get("export") or [])
    snapshot["compliance"] = cons.get("compliance")
    snapshot["consumption_fetched_at"] = cons.get("last_fetch_at")
    if cons.get("errors"):
        snapshot["errors"].update(cons["errors"])

    if not api_key:
        snapshot["errors"]["auth"] = "Octopus API key required for live rates and meter polling"
        return snapshot

    if not snapshot["consumption"] and not snapshot["errors"].get("consumption"):
        snapshot["errors"]["consumption"] = (
            "Smart-meter consumption will populate after the next half-hourly Octopus poll"
        )

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
    return {
        **snapshot,
        "greener_title": greener.get("title"),
        "carbon_periods": greener.get("carbon_periods") or snapshot.get("carbon_periods") or [],
        "timeline": greener.get("timeline") or [],
        "green_threshold_gco2": greener.get("green_threshold_gco2") or GREEN_THRESHOLD_GCO2,
        "rewards": greener.get("rewards"),
        "greener_history_count": greener.get("history_count"),
        "postcode": greener.get("postcode"),
        "errors": {**(greener.get("errors") or {}), **(snapshot.get("errors") or {})},
        "variable_tariff": is_variable_tariff_type(str(snapshot.get("tariff_type") or "")),
    }
