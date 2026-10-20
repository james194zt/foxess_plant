"""SmartCharge day view: each half-hour of a local day, as planned and as it actually happened.

Plan: the plan_slots table (the plan for each half-hour as it stood when the half-hour began, written at every
replan since 0.9.541). Older days fall back to the HEMS audit's daily-plan events, which only list the charge
and export half-hours (no predicted SoC). Actual: battery SoC from the recorder, and grid charge / battery
export per half-hour from the power sensors' statistics.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

UTC = timezone.utc
HALF_HOUR = timedelta(minutes=30)
# Below this per half-hour the CT's low-power error (tens of watts) can't fake a charge or an export
ACTION_THRESHOLD_KWH = 0.1
CHARGE_ACTIONS = ("charge", "spread_charge", "winter_fill", "solar_gap_fill", "arbitrage", "charge_candidate")
EXPORT_ACTIONS = ("export", "spread_export")


def utc_key(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(raw: Any) -> datetime | None:
    if not raw:
        return None
    parsed = dt_util.parse_datetime(str(raw).replace("Z", "+00:00"))
    if parsed is None:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def plan_slot_rows(plan: list[dict[str, Any]], now: datetime, *, built_at: str | None) -> list[dict[str, Any]]:
    """Rows for the plan_slots table: only half-hours that haven't started (the running one keeps its plan)."""
    rows: list[dict[str, Any]] = []
    for slot in plan or []:
        start = parse_utc(slot.get("start_utc"))
        if start is None or start <= now:
            continue
        end = parse_utc(slot.get("end_utc"))
        rows.append(
            {
                "start_utc": utc_key(start),
                "end_utc": utc_key(end) if end else None,
                "action": slot.get("action"),
                "reason": slot.get("reason"),
                "planned_import_kwh": slot.get("planned_import_kwh"),
                "planned_export_kwh": slot.get("planned_export_kwh"),
                "soc_start_pct": slot.get("soc_start_pct"),
                "soc_end_pct": slot.get("soc_end_pct"),
                "import_p_per_kwh": slot.get("import_p_per_kwh"),
                "export_p_per_kwh": slot.get("export_p_per_kwh"),
                "built_at": built_at,
            }
        )
    return rows


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """Local midnight to next local midnight, as UTC datetimes (23 or 25 hours on clock-change days)."""
    tz = dt_util.get_default_time_zone()
    start = datetime(day.year, day.month, day.day, tzinfo=tz)
    nxt = day + timedelta(days=1)
    end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz)
    return start.astimezone(UTC), end.astimezone(UTC)


def day_slots(day: date) -> list[tuple[datetime, datetime]]:
    start, end = day_bounds(day)
    out = []
    t = start
    while t < end:
        out.append((t, t + HALF_HOUR))
        t += HALF_HOUR
    return out


def _value_at(points: list[tuple[float, float]], t_ms: float) -> float | None:
    """Last known value at or before t (points sorted by time)."""
    value = None
    for ts, v in points:
        if ts > t_ms:
            break
        value = v
    return value


def _audit_plan_at(events: list[dict[str, Any]], start: datetime) -> dict[str, Any] | None:
    """The daily-plan audit event in force when a half-hour began, as {action, planned_import_kwh, ...}."""
    in_force = None
    for event in events:  # oldest first
        ts = parse_utc(event.get("ts"))
        if ts is None or ts > start:
            break
        in_force = event
    if in_force is None:
        return None
    key = utc_key(start)
    for slot in (in_force.get("payload") or {}).get("slots") or []:
        slot_start = parse_utc(slot.get("start_utc"))
        if slot_start is not None and utc_key(slot_start) == key:
            return {
                "action": slot.get("action"),
                "reason": slot.get("reason"),
                "planned_import_kwh": slot.get("planned_import_kwh"),
                "planned_export_kwh": slot.get("planned_export_kwh"),
            }
    # The audit lists only charge/export half-hours, so anything else was self-use
    return {"action": "idle", "reason": "self_use"}


def build_day(
    *,
    day: date,
    now: datetime,
    plan_rows: list[dict[str, Any]],
    audit_events: list[dict[str, Any]],
    soc_points: list[tuple[float, float]],
    kwh_in: Any,
) -> dict[str, Any]:
    """Planned vs actual for each half-hour of ``day``.

    ``kwh_in(key, start_ms, end_ms)`` returns energy for one of battery_charge / battery_discharge /
    grid_import / grid_export in that window (kWh), or None when that sensor isn't available.
    """
    stored = {row["start_utc"]: row for row in plan_rows}
    events = sorted(audit_events, key=lambda e: str(e.get("ts") or ""))
    tz = dt_util.get_default_time_zone()
    slots: list[dict[str, Any]] = []
    sources: set[str] = set()
    for start, end in day_slots(day):
        key = utc_key(start)
        row = stored.get(key)
        if row is not None:
            plan = {k: row.get(k) for k in (
                "action", "reason", "planned_import_kwh", "planned_export_kwh",
                "soc_start_pct", "soc_end_pct", "import_p_per_kwh", "export_p_per_kwh",
            )}
            sources.add("stored")
        else:
            plan = _audit_plan_at(events, start) if start <= now else None
            if plan is not None:
                sources.add("audit")
        actual = None
        if start < now:
            s_ms, e_ms = start.timestamp() * 1000, min(end, now).timestamp() * 1000
            charge = kwh_in("battery_charge", s_ms, e_ms)
            discharge = kwh_in("battery_discharge", s_ms, e_ms)
            imp = kwh_in("grid_import", s_ms, e_ms)
            exp = kwh_in("grid_export", s_ms, e_ms)
            grid_charge = min(charge, imp) if charge is not None and imp is not None else None
            batt_export = min(discharge, exp) if discharge is not None and exp is not None else None
            if grid_charge is not None and grid_charge >= ACTION_THRESHOLD_KWH:
                action = "charge"
            elif batt_export is not None and batt_export >= ACTION_THRESHOLD_KWH:
                action = "export"
            else:
                action = "idle"
            actual = {
                "action": action,
                "grid_charge_kwh": round(grid_charge, 3) if grid_charge is not None else None,
                "battery_export_kwh": round(batt_export, 3) if batt_export is not None else None,
                "battery_charge_kwh": round(charge, 3) if charge is not None else None,
                "battery_discharge_kwh": round(discharge, 3) if discharge is not None else None,
                "soc_start_pct": _value_at(soc_points, s_ms),
                "soc_end_pct": _value_at(soc_points, e_ms),
            }
        local = start.astimezone(tz)
        slots.append(
            {
                "start_utc": key,
                "end_utc": utc_key(end),
                "start": local.strftime("%H:%M"),
                "end": end.astimezone(tz).strftime("%H:%M"),
                "plan": plan,
                "actual": actual,
            }
        )
    return {"date": day.isoformat(), "slots": slots, "summary": _summary(slots), "plan_source": _source(sources)}


def _source(sources: set[str]) -> str | None:
    if not sources:
        return None
    return "stored" if sources == {"stored"} else "audit" if sources == {"audit"} else "mixed"


def _summary(slots: list[dict[str, Any]]) -> dict[str, Any]:
    def total(rows: list[Any], key: str) -> float | None:
        vals = [float(r[key]) for r in rows if r and r.get(key) is not None]
        return round(sum(vals), 2) if vals else None

    plans = [s["plan"] for s in slots if s["plan"]]
    actuals = [s["actual"] for s in slots if s["actual"]]
    planned_charge = total([p for p in plans if p.get("action") in CHARGE_ACTIONS], "planned_import_kwh")
    planned_export = total([p for p in plans if p.get("action") in EXPORT_ACTIONS], "planned_export_kwh")
    socs = [a[k] for a in actuals for k in ("soc_start_pct", "soc_end_pct") if a.get(k) is not None]
    # What the actual grid charge cost, where the plan knew the price of that half-hour
    cost_p = 0.0
    costed = False
    for s in slots:
        a, p = s["actual"], s["plan"]
        if a and p and a.get("grid_charge_kwh") and p.get("import_p_per_kwh") is not None:
            cost_p += float(a["grid_charge_kwh"]) * float(p["import_p_per_kwh"])
            costed = True
    return {
        "planned_charge_kwh": planned_charge,
        "actual_charge_kwh": total([a for a in actuals if a.get("action") == "charge"], "grid_charge_kwh"),
        "planned_export_kwh": planned_export,
        "actual_export_kwh": total([a for a in actuals if a.get("action") == "export"], "battery_export_kwh"),
        "soc_start_pct": actuals[0].get("soc_start_pct") if actuals else None,
        "soc_end_pct": actuals[-1].get("soc_end_pct") if actuals else None,
        "soc_min_pct": min(socs) if socs else None,
        "soc_max_pct": max(socs) if socs else None,
        "charge_cost_p": round(cost_p, 1) if costed else None,
    }


async def async_build_smart_charge_day(hass: Any, coordinator: Any, day: date) -> dict[str, Any]:
    """Day view payload; recorder and SQLite reads run in the recorder executor."""
    from homeassistant.components.recorder import get_instance

    from .discovery import resolve_entity_id
    from .smart_charge_analysis import POWER_KEYS, power_unit_scale

    entity_map = coordinator.plant.entity_map or {}
    device_id = coordinator.plant.device_id
    power_ids: dict[str, str | None] = {}
    scales: dict[str, float] = {}
    for key in POWER_KEYS:
        eid = resolve_entity_id(hass, entity_map, key, device_id=device_id)
        power_ids[key] = eid
        state = hass.states.get(eid) if eid else None
        scales[key] = power_unit_scale(state.attributes.get("unit_of_measurement") if state is not None else None)
    soc_id = resolve_entity_id(hass, entity_map, "battery_soc", device_id=device_id)
    store = getattr(coordinator, "_performance_store", None)
    now = dt_util.utcnow()

    def job() -> dict[str, Any]:
        return _build_sync(hass, day=day, now=now, power_ids=power_ids, scales=scales, soc_id=soc_id, store=store)

    return await get_instance(hass).async_add_executor_job(job)


def _build_sync(
    hass: Any,
    *,
    day: date,
    now: datetime,
    power_ids: dict[str, str | None],
    scales: dict[str, float],
    soc_id: str | None,
    store: Any,
) -> dict[str, Any]:
    from .performance.hems_audit import EVENT_DAILY_PLAN
    from .smart_charge_analysis import (
        SHORT_TERM_STATS_DAYS,
        _recorder_states,
        _state_timestamp_ms,
        integrate_power_kwh,
        stats_rows_to_power_points,
    )
    from .websocket_api import _fetch_statistics_points

    start, end = day_bounds(day)
    fetch_end = min(end, now)

    power: dict[str, list[dict[str, float]]] = {}
    ids = [eid for eid in power_ids.values() if eid]
    if ids and fetch_end > start:
        # 5-minute statistics while they're kept (~10 days), hourly after that
        period = "5minute" if now - start <= timedelta(days=SHORT_TERM_STATS_DAYS) else "hour"
        try:
            rows = _fetch_statistics_points(hass, start - HALF_HOUR, fetch_end, ids, period=period, statistic="mean")
            for key, eid in power_ids.items():
                if eid:
                    pts = stats_rows_to_power_points(rows.get(eid) or [])
                    power[key] = [{"t": p["t"], "v": p["v"] * scales.get(key, 1.0)} for p in pts]
        except Exception as err:  # noqa: BLE001 — the plan still shows without actuals
            _LOGGER.warning("SmartCharge day statistics failed: %s", err)

    def kwh_in(key: str, s_ms: float, e_ms: float) -> float | None:
        pts = power.get(key)
        if not pts:
            return None
        return integrate_power_kwh(pts, s_ms, e_ms)

    soc_points: list[tuple[float, float]] = []
    if soc_id and fetch_end > start:
        try:
            for state in _recorder_states(hass, soc_id, start - timedelta(hours=1), fetch_end, attributes=False):
                t_ms = _state_timestamp_ms(state)
                try:
                    value = float(state.state)
                except (TypeError, ValueError):
                    continue
                if t_ms is not None:
                    soc_points.append((t_ms, value))
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("SmartCharge day SoC history failed: %s", err)
    soc_points.sort()

    plan_rows: list[dict[str, Any]] = []
    audit_events: list[dict[str, Any]] = []
    if store is not None:
        try:
            plan_rows = store.list_plan_slots_between(utc_key(start), utc_key(end))
            # Plan in force at midnight may have been logged up to a couple of days before
            audit_events = store.list_events_between(
                (start - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
                end.strftime("%Y-%m-%dT%H:%M:%S"),
                event_types=[EVENT_DAILY_PLAN],
                limit=500,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("SmartCharge day plan history failed: %s", err)

    payload = build_day(
        day=day, now=now, plan_rows=plan_rows, audit_events=audit_events, soc_points=soc_points, kwh_in=kwh_in
    )
    payload["is_today"] = dt_util.as_local(now).date() == day
    payload["missing_sensors"] = [k for k, v in power_ids.items() if not v] + ([] if soc_id else ["battery_soc"])
    return payload
