"""SmartCharge Analysis report — planned vs actual grid import/export from recorder history."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

CHARGE_PLAN_ACTIONS = frozenset({"charge", "spread_charge", "winter_fill", "solar_gap_fill"})
EXPORT_PLAN_ACTIONS = frozenset({"export", "spread_export"})


def reports_period_bounds(
    period: str,
    offset: int = 0,
    *,
    now: datetime | None = None,
) -> tuple[datetime, datetime, bool]:
    """Match panel REPORTS_PERIOD_TABS (week / month / year). Returns start, end, can_next."""
    local_now = dt_util.as_local(now or dt_util.now())
    o = max(0, int(offset or 0))

    if period == "week":
        start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        start -= timedelta(days=start.weekday())
        start -= timedelta(days=o * 7)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        return start, end, o > 0

    if period == "month":
        year = local_now.year
        month = local_now.month - o
        while month < 1:
            month += 12
            year -= 1
        start = local_now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
        if month == 12:
            next_month = start.replace(year=year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=month + 1, day=1)
        end = next_month - timedelta(microseconds=1)
        return start, end, o > 0

    if period == "year":
        year = local_now.year - o
        start = local_now.replace(year=year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = local_now.replace(year=year, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        return start, end, o > 0

    start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    start -= timedelta(days=o * 7)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    return start, end, o > 0


def reports_period_label(period: str, offset: int = 0, *, now: datetime | None = None) -> str:
    start, end, _ = reports_period_bounds(period, offset, now=now)
    if period == "month":
        return start.strftime("%B %Y")
    if period == "year":
        return str(start.year)
    return f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"


def find_entry_entity(hass: HomeAssistant, entry_id: str, unique_suffix: str) -> str | None:
    """Resolve a FoxESS Plant entity id from config entry + unique_id suffix."""
    registry = er.async_get(hass)
    for ent in registry.entities.values():
        if ent.config_entry_id != entry_id:
            continue
        uid = ent.unique_id or ""
        if uid.endswith(unique_suffix) or ent.entity_id.endswith(unique_suffix):
            return ent.entity_id
    return None


def _state_timestamp_ms(state: Any) -> float | None:
    if isinstance(state, dict):
        ts_raw = (
            state.get("last_updated")
            or state.get("last_changed")
            or state.get("lu")
            or state.get("lc")
        )
    else:
        ts_raw = getattr(state, "last_updated", None) or getattr(state, "last_changed", None)
    if ts_raw is None:
        return None
    if isinstance(ts_raw, (int, float)):
        return float(ts_raw) * 1000 if ts_raw < 1e12 else float(ts_raw)
    parsed = dt_util.parse_datetime(str(ts_raw))
    if parsed is None:
        return None
    return dt_util.as_utc(parsed).timestamp() * 1000


def _state_value_on(state: Any) -> bool:
    if isinstance(state, dict):
        raw = state.get("state", state.get("s"))
    else:
        raw = getattr(state, "state", None)
    return str(raw).lower() in ("on", "true", "1")


def _state_attrs(state: Any) -> dict[str, Any]:
    if isinstance(state, dict):
        attrs = state.get("attributes")
    else:
        attrs = getattr(state, "attributes", None)
    return attrs if isinstance(attrs, dict) else {}


def pair_binary_on_periods(
    states: list[Any],
    *,
    range_end_ms: float,
) -> list[dict[str, Any]]:
    """Pair binary_sensor on/off transitions into {start_ms, end_ms} windows."""
    events: list[tuple[float, bool]] = []
    for state in states:
        t_ms = _state_timestamp_ms(state)
        if t_ms is None:
            continue
        if isinstance(state, dict) and "v" in state and "t" in state:
            events.append((t_ms, float(state["v"]) > 0))
        else:
            events.append((t_ms, _state_value_on(state)))
    events.sort(key=lambda item: item[0])
    periods: list[dict[str, Any]] = []
    open_start: float | None = None
    for t_ms, is_on in events:
        if is_on and open_start is None:
            open_start = t_ms
        elif not is_on and open_start is not None:
            periods.append({"start_ms": open_start, "end_ms": t_ms})
            open_start = None
    if open_start is not None:
        periods.append({"start_ms": open_start, "end_ms": range_end_ms})
    return periods


def integrate_power_kwh(
    points: list[dict[str, float]],
    start_ms: float,
    end_ms: float,
) -> float:
    """Trapezoidal integration of kW samples → kWh within [start_ms, end_ms]."""
    if end_ms <= start_ms or not points:
        return 0.0
    normalized = [_normalize_power_point(p) for p in points]
    normalized = [p for p in normalized if p is not None]
    if not normalized:
        return 0.0
    clipped = [p for p in normalized if start_ms <= p["t"] <= end_ms]
    if not clipped:
        before = [p for p in normalized if p["t"] < start_ms]
        after = [p for p in normalized if p["t"] > end_ms]
        if not before:
            return 0.0
        v0 = before[-1]["v"]
        v1 = after[0]["v"] if after else v0
        hours = (end_ms - start_ms) / 3_600_000
        return max(0.0, ((v0 + v1) / 2) * hours)
    seq = list(clipped)
    before = [p for p in normalized if p["t"] < start_ms]
    if before and seq[0]["t"] > start_ms:
        seq.insert(0, {"t": start_ms, "v": before[-1]["v"]})
    after = [p for p in normalized if p["t"] > end_ms]
    if after and seq[-1]["t"] < end_ms:
        seq.append({"t": end_ms, "v": after[0]["v"]})
    elif seq[-1]["t"] < end_ms:
        seq.append({"t": end_ms, "v": seq[-1]["v"]})
    total = 0.0
    for i in range(len(seq) - 1):
        t0, v0 = seq[i]["t"], max(0.0, float(seq[i]["v"]))
        t1, v1 = seq[i + 1]["t"], max(0.0, float(seq[i + 1]["v"]))
        if t1 <= t0:
            continue
        total += ((v0 + v1) / 2.0) * ((t1 - t0) / 3_600_000.0)
    return round(max(0.0, total), 3)


def _normalize_power_point(point: dict[str, Any] | None) -> dict[str, float] | None:
    """Accept {t,v} chart points or recorder stats rows {start, mean}."""
    if not isinstance(point, dict):
        return None
    if "t" in point and "v" in point:
        try:
            return {"t": float(point["t"]), "v": float(point["v"])}
        except (TypeError, ValueError):
            return None
    raw_start = point.get("start")
    raw_mean = point.get("mean")
    if raw_start is None or raw_mean is None:
        return None
    try:
        t_ms = float(raw_start)
        if t_ms < 1e12:
            t_ms *= 1000.0
        return {"t": t_ms, "v": float(raw_mean)}
    except (TypeError, ValueError):
        return None


def stats_rows_to_power_points(rows: list[dict[str, Any]] | None) -> list[dict[str, float]]:
    """Convert _fetch_statistics_points rows into integrate_power_kwh points."""
    out: list[dict[str, float]] = []
    for row in rows or []:
        pt = _normalize_power_point(row)
        if pt is not None:
            out.append(pt)
    out.sort(key=lambda p: p["t"])
    return out


def resolve_slot_range_ms(anchor: datetime, start_s: str, end_s: str) -> tuple[int, int] | None:
    """Resolve HH:MM plan slot times relative to anchor local day."""
    try:
        sh, sm = (int(x) for x in str(start_s).split(":", 1))
        eh, em = (int(x) for x in str(end_s).split(":", 1))
    except (TypeError, ValueError, IndexError):
        return None
    local = dt_util.as_local(anchor)
    start = local.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end = local.replace(hour=eh, minute=em, second=0, microsecond=0)
    if end <= start:
        end += timedelta(days=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def expand_plan_slots(
    daily_plan: list[dict[str, Any]] | None,
    *,
    anchor: datetime,
    range_start_ms: float,
    range_end_ms: float,
) -> list[dict[str, Any]]:
    """Expand daily_plan HH:MM slots into absolute windows within the report range."""
    if not daily_plan:
        return []
    out: list[dict[str, Any]] = []
    for entry in daily_plan:
        action = str(entry.get("action") or "")
        if action in ("idle", "charge_candidate"):
            continue
        bounds = None
        start_utc = dt_util.parse_datetime(str(entry.get("start_utc") or ""))
        end_utc = dt_util.parse_datetime(str(entry.get("end_utc") or ""))
        if start_utc is not None and end_utc is not None:
            bounds = (int(start_utc.timestamp() * 1000), int(end_utc.timestamp() * 1000))
        else:
            bounds = resolve_slot_range_ms(anchor, entry.get("start", ""), entry.get("end", ""))
        if bounds is None:
            continue
        start_ms, end_ms = bounds
        if end_ms < range_start_ms or start_ms > range_end_ms:
            continue
        slot = {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "action": action,
            "reason": entry.get("reason"),
            "import_p_per_kwh": entry.get("import_p_per_kwh"),
            "export_p_per_kwh": entry.get("export_p_per_kwh"),
            "planned_export_kwh": entry.get("planned_export_kwh"),
            "expected_spread_p_per_kwh": entry.get("expected_spread_p_per_kwh"),
        }
        if entry.get("planned_import_kwh") is not None:
            slot["planned_import_kwh"] = entry.get("planned_import_kwh")
        out.append(slot)
    return sorted(out, key=lambda row: row["start_ms"])


def collect_plan_snapshots(
    states: list[Any],
    *,
    range_start_ms: float,
    range_end_ms: float,
) -> list[dict[str, Any]]:
    """Extract daily_plan revisions from smart charge decision sensor history."""
    snapshots: list[dict[str, Any]] = []
    seen_sigs: set[str] = set()
    for state in states:
        t_ms = _state_timestamp_ms(state)
        if t_ms is None or t_ms < range_start_ms - 86_400_000 or t_ms > range_end_ms:
            continue
        attrs = _state_attrs(state)
        daily_plan = attrs.get("daily_plan")
        if not isinstance(daily_plan, list) or not daily_plan:
            continue
        sig = str(daily_plan[0].get("plan_horizon", "")) + "|" + str(len(daily_plan))
        for row in daily_plan[:3]:
            sig += f"|{row.get('action')}:{row.get('start')}"
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)
        anchor = dt_util.as_local(datetime.fromtimestamp(t_ms / 1000, tz=dt_util.UTC))
        snapshots.append(
            {
                "captured_ms": t_ms,
                "operating_mode": attrs.get("operating_mode"),
                "grid_gap_kwh": (attrs.get("decision") or {}).get("grid_gap_kwh")
                or daily_plan[0].get("grid_gap_kwh"),
                "spread_pairs": daily_plan[0].get("spread_pairs") or attrs.get("spread_pairs"),
                "expected_spread_profit_p": daily_plan[0].get("expected_spread_profit_p"),
                "slots": expand_plan_slots(
                    daily_plan,
                    anchor=anchor,
                    range_start_ms=range_start_ms,
                    range_end_ms=range_end_ms,
                ),
            }
        )
    return sorted(snapshots, key=lambda row: row["captured_ms"])


def _allocate_planned_import_kwh(slots: list[dict[str, Any]], grid_gap_kwh: float | None) -> None:
    charge_slots = [s for s in slots if s.get("action") in CHARGE_PLAN_ACTIONS]
    if any(s.get("planned_import_kwh") is not None for s in charge_slots):
        return  # planner already sized each slot
    if not charge_slots or not grid_gap_kwh:
        return
    total_min = sum(max(1, (s["end_ms"] - s["start_ms"]) // 60_000) for s in charge_slots)
    for slot in charge_slots:
        minutes = max(1, (slot["end_ms"] - slot["start_ms"]) // 60_000)
        slot["planned_import_kwh"] = round(float(grid_gap_kwh) * minutes / total_min, 3)


def decision_context_at(decision_states: list[Any], t_ms: float) -> dict[str, Any]:
    """Nearest decision sensor state at or before t_ms."""
    best: dict[str, Any] = {}
    best_t = -1.0
    for state in decision_states:
        ts = _state_timestamp_ms(state)
        if ts is None or ts > t_ms or ts < best_t:
            continue
        attrs = _state_attrs(state)
        best_t = ts
        best = {
            "action": (
                attrs.get("decision", {}).get("action")
                if isinstance(attrs.get("decision"), dict)
                else None
            ),
            "reason": attrs.get("reason")
            or (
                attrs.get("decision", {}).get("reason")
                if isinstance(attrs.get("decision"), dict)
                else None
            ),
            "discharge_armed": bool(attrs.get("discharge_armed")),
            "armed": bool(attrs.get("armed")),
            "operating_mode": attrs.get("operating_mode"),
        }
        if isinstance(state, dict):
            best["state"] = state.get("state", state.get("s"))
        else:
            best["state"] = getattr(state, "state", None)
    if not best:
        return {"direction": "import", "action": "unknown", "reason": None}
    if best.get("discharge_armed") or str(best.get("reason") or "").startswith("smart_charge:export"):
        direction = "export"
    else:
        direction = "import"
    return {**best, "direction": direction}


def build_daily_chart(
    sessions: list[dict[str, Any]],
    planned_slots: list[dict[str, Any]],
    *,
    range_start_ms: float,
    range_end_ms: float,
) -> list[dict[str, Any]]:
    """Per-day actual vs planned import/export totals."""
    by_day: dict[str, dict[str, float]] = {}

    def day_key(ms: float) -> str:
        d = dt_util.as_local(datetime.fromtimestamp(ms / 1000, tz=dt_util.UTC))
        return d.strftime("%Y-%m-%d")

    cursor = dt_util.as_local(datetime.fromtimestamp(range_start_ms / 1000, tz=dt_util.UTC)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end_local = dt_util.as_local(datetime.fromtimestamp(range_end_ms / 1000, tz=dt_util.UTC))
    while cursor <= end_local:
        by_day[cursor.strftime("%Y-%m-%d")] = {
            "import_actual_kwh": 0.0,
            "export_actual_kwh": 0.0,
            "import_planned_kwh": 0.0,
            "export_planned_kwh": 0.0,
        }
        cursor += timedelta(days=1)

    for session in sessions:
        key = day_key(session["start_ms"])
        if key not in by_day:
            continue
        if session.get("direction") == "export":
            by_day[key]["export_actual_kwh"] += float(session.get("actual_export_kwh") or 0)
        else:
            by_day[key]["import_actual_kwh"] += float(session.get("actual_import_kwh") or 0)

    for slot in planned_slots:
        key = day_key(slot["start_ms"])
        if key not in by_day:
            continue
        if slot.get("action") in EXPORT_PLAN_ACTIONS:
            by_day[key]["export_planned_kwh"] += float(slot.get("planned_export_kwh") or 0)
        elif slot.get("action") in CHARGE_PLAN_ACTIONS:
            by_day[key]["import_planned_kwh"] += float(slot.get("planned_import_kwh") or 0)

    return [
        {"date": date, **{k: round(v, 3) for k, v in vals.items()}}
        for date, vals in sorted(by_day.items())
    ]


def collect_daily_economics(
    decision_states: list[Any],
    *,
    range_start_ms: float,
    range_end_ms: float,
) -> dict[str, dict[str, Any]]:
    """Per local day, the latest plan SmartCharge built that day — its own cost/saving figures.

    Reads ``decision.plan_summary`` (cost_p, baseline_cost_p, saving_p, planned grid charge/export,
    PV/load forecast) so the report can show what SmartCharge decided and why, even on days it chose
    to do nothing (idle/self-use), which carry no plan slots.
    """
    by_day: dict[str, dict[str, Any]] = {}
    for state in decision_states:
        attrs = _state_attrs(state)
        decision = attrs.get("decision")
        summary = decision.get("plan_summary") if isinstance(decision, dict) else None
        if not isinstance(summary, dict):
            continue
        built = dt_util.parse_datetime(str(summary.get("built_at") or ""))
        t_ms = dt_util.as_utc(built).timestamp() * 1000 if built is not None else _state_timestamp_ms(state)
        if t_ms is None or t_ms < range_start_ms - 86_400_000 or t_ms > range_end_ms:
            continue
        day = dt_util.as_local(datetime.fromtimestamp(t_ms / 1000, tz=dt_util.UTC)).strftime("%Y-%m-%d")
        reason = attrs.get("reason") or (decision.get("reason") if isinstance(decision, dict) else None)
        mode = summary.get("operating_mode") or (
            decision.get("operating_mode") if isinstance(decision, dict) else None
        )
        row = {
            "built_ms": float(t_ms),
            "reason": reason,
            "operating_mode": mode,
            "saving_p": summary.get("saving_p"),
            "cost_p": summary.get("cost_p"),
            "baseline_cost_p": summary.get("baseline_cost_p"),
            "planned_grid_charge_kwh": summary.get("grid_charge_kwh"),
            "planned_export_kwh": summary.get("export_kwh"),
            "pv_kwh": summary.get("pv_kwh"),
            "load_kwh": summary.get("load_kwh"),
            "tomorrow_pv_kwh": summary.get("tomorrow_pv_kwh"),
        }
        prev = by_day.get(day)
        if prev is None or row["built_ms"] >= prev["built_ms"]:
            by_day[day] = row
    return by_day


def _local_day_key(ms: float) -> str:
    return dt_util.as_local(datetime.fromtimestamp(ms / 1000, tz=dt_util.UTC)).strftime("%Y-%m-%d")


def _merge_windows(windows: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Merge overlapping/adjacent (start, end) windows so a night's revised slots aren't counted twice."""
    ordered = sorted((min(a, b), max(a, b)) for a, b in windows)
    merged: list[tuple[float, float]] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _integrate_over_windows(points: list[dict[str, float]], windows: list[tuple[float, float]]) -> float:
    if not windows:
        return 0.0
    return round(sum(integrate_power_kwh(points, s, e) for s, e in _merge_windows(windows)), 3)


def build_how_used(
    *,
    daily_economics: dict[str, dict[str, Any]],
    planned_slots: list[dict[str, Any]],
    battery_charge_pts: list[dict[str, float]],
    grid_export_pts: list[dict[str, float]],
    range_start_ms: float,
    range_end_ms: float,
) -> list[dict[str, Any]]:
    """Per-day 'what SmartCharge did': planned vs actual, the reason, and its own saving figure.

    Planned kWh comes from the plan's own ``grid_charge_kwh`` (authoritative — summing slots double-counts
    plan revisions). Actual charge is battery charging during the planned overnight windows (grid import
    there is mostly base household load, so it misreads as a charge). Gives a clean charged / skipped
    (solar covered) / exported / self-use status.
    """
    days: dict[str, dict[str, Any]] = {}
    cursor = dt_util.as_local(datetime.fromtimestamp(range_start_ms / 1000, tz=dt_util.UTC)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end_local = dt_util.as_local(datetime.fromtimestamp(range_end_ms / 1000, tz=dt_util.UTC))
    while cursor <= end_local:
        days[cursor.strftime("%Y-%m-%d")] = {
            "charge_windows": [],
            "export_windows": [],
            "slot_planned_charge_kwh": 0.0,
            "charge_rate_p": None,
        }
        cursor += timedelta(days=1)

    for slot in planned_slots:
        day = days.get(_local_day_key(slot["start_ms"]))
        if day is None:
            continue
        if slot.get("action") in CHARGE_PLAN_ACTIONS:
            day["charge_windows"].append((slot["start_ms"], slot["end_ms"]))
            day["slot_planned_charge_kwh"] += float(slot.get("planned_import_kwh") or 0)
            rate = slot.get("import_p_per_kwh")
            if rate is not None:
                day["charge_rate_p"] = rate if day["charge_rate_p"] is None else min(day["charge_rate_p"], rate)
        elif slot.get("action") in EXPORT_PLAN_ACTIONS:
            day["export_windows"].append((slot["start_ms"], slot["end_ms"]))

    rows: list[dict[str, Any]] = []
    for date, d in sorted(days.items()):
        econ = daily_economics.get(date) or {}
        planned_c = econ.get("planned_grid_charge_kwh")
        if planned_c is None:
            planned_c = d["slot_planned_charge_kwh"]
        planned_c = round(float(planned_c or 0), 3)
        planned_e = round(float(econ.get("planned_export_kwh") or 0), 3)
        actual_c = _integrate_over_windows(battery_charge_pts, d["charge_windows"])
        actual_e = _integrate_over_windows(grid_export_pts, d["export_windows"])
        if planned_c > 0.05:
            status = "charged" if actual_c > 0.3 else "skipped"
        elif planned_e > 0.05 or actual_e > 0.1:
            status = "exported"
        elif econ:
            status = "self_use"
        else:
            status = "no_data"
        rows.append(
            {
                "date": date,
                "status": status,
                "reason": econ.get("reason"),
                "operating_mode": econ.get("operating_mode"),
                "planned_charge_kwh": planned_c,
                "actual_charge_kwh": actual_c,
                "planned_export_kwh": planned_e,
                "actual_export_kwh": actual_e,
                "charge_rate_p": d["charge_rate_p"],
                "saving_p": econ.get("saving_p"),
                "cost_p": econ.get("cost_p"),
                "baseline_cost_p": econ.get("baseline_cost_p"),
                "pv_kwh": econ.get("pv_kwh"),
                "load_kwh": econ.get("load_kwh"),
            }
        )
    return rows


def _how_used_summary(how_used: list[dict[str, Any]]) -> dict[str, Any]:
    savings = [float(r["saving_p"]) for r in how_used if r.get("saving_p") is not None]
    return {
        "estimated_saving_p": round(sum(savings), 2) if savings else None,
        "planned_grid_charge_kwh": round(sum(float(r["planned_charge_kwh"]) for r in how_used), 3),
        "actual_grid_charge_kwh": round(sum(float(r["actual_charge_kwh"]) for r in how_used), 3),
        "nights_charged": sum(1 for r in how_used if r["status"] == "charged"),
        "nights_skipped_solar": sum(1 for r in how_used if r["status"] == "skipped"),
        "days_exported": sum(1 for r in how_used if r["status"] == "exported"),
    }


def build_smart_charge_analysis_payload(
    *,
    period: str,
    offset: int,
    period_label: str,
    range_start_ms: float,
    range_end_ms: float,
    armed_periods: list[dict[str, Any]],
    decision_states: list[Any],
    grid_import_pts: list[dict[str, float]],
    grid_export_pts: list[dict[str, float]],
    battery_charge_pts: list[dict[str, float]],
    battery_discharge_pts: list[dict[str, float]],
    plan_snapshots: list[dict[str, Any]],
    operating_mode: str | None,
) -> dict[str, Any]:
    """Assemble report JSON from recorder samples."""
    planned_slots: list[dict[str, Any]] = []
    for snap in plan_snapshots:
        grid_gap = snap.get("grid_gap_kwh")
        slots = list(snap.get("slots") or [])
        _allocate_planned_import_kwh(slots, grid_gap)
        for slot in slots:
            slot["plan_captured_ms"] = snap.get("captured_ms")
            planned_slots.append(slot)

    deduped: dict[str, dict[str, Any]] = {}
    for slot in planned_slots:
        key = f"{slot['start_ms']}:{slot.get('action')}"
        deduped[key] = slot
    planned_slots = sorted(deduped.values(), key=lambda row: row["start_ms"])
    # Mark whether each planned window was actually used: battery charging (grid charge) or grid export
    # during the slot. Lets the UI show predicted vs actual instead of looking like it definitely ran.
    for slot in planned_slots:
        if slot.get("action") in CHARGE_PLAN_ACTIONS:
            slot["actual_kwh"] = integrate_power_kwh(battery_charge_pts, slot["start_ms"], slot["end_ms"])
        elif slot.get("action") in EXPORT_PLAN_ACTIONS:
            slot["actual_kwh"] = integrate_power_kwh(grid_export_pts, slot["start_ms"], slot["end_ms"])
        else:
            slot["actual_kwh"] = None

    sessions: list[dict[str, Any]] = []
    for period_row in armed_periods:
        start_ms = float(period_row["start_ms"])
        end_ms = float(period_row["end_ms"])
        ctx = decision_context_at(decision_states, start_ms)
        direction = ctx.get("direction", "import")
        actual_import = integrate_power_kwh(grid_import_pts, start_ms, end_ms)
        actual_export = integrate_power_kwh(grid_export_pts, start_ms, end_ms)
        batt_charge = integrate_power_kwh(battery_charge_pts, start_ms, end_ms)
        batt_discharge = integrate_power_kwh(battery_discharge_pts, start_ms, end_ms)
        matched = None
        for slot in planned_slots:
            if slot["start_ms"] <= start_ms < slot["end_ms"] or (
                start_ms <= slot["start_ms"] < end_ms
            ):
                matched = slot
                break
        duration_min = max(1, round((end_ms - start_ms) / 60_000))
        sessions.append(
            {
                "start_ms": int(start_ms),
                "end_ms": int(end_ms),
                "duration_min": duration_min,
                "direction": direction,
                "action": ctx.get("action") or ctx.get("state") or "armed",
                "reason": ctx.get("reason"),
                "actual_import_kwh": actual_import if direction == "import" else 0.0,
                "actual_export_kwh": actual_export if direction == "export" else 0.0,
                "battery_charge_kwh": batt_charge,
                "battery_discharge_kwh": batt_discharge,
                "planned_import_kwh": matched.get("planned_import_kwh") if matched and direction == "import" else None,
                "planned_export_kwh": matched.get("planned_export_kwh") if matched and direction == "export" else None,
                "import_p_per_kwh": matched.get("import_p_per_kwh") if matched else None,
                "export_p_per_kwh": matched.get("export_p_per_kwh") if matched else None,
            }
        )

    import_actual = round(sum(s["actual_import_kwh"] for s in sessions), 3)
    export_actual = round(sum(s["actual_export_kwh"] for s in sessions), 3)
    import_planned = round(
        sum(float(s.get("planned_import_kwh") or 0) for s in planned_slots if s.get("action") in CHARGE_PLAN_ACTIONS),
        3,
    )
    export_planned = round(
        sum(float(s.get("planned_export_kwh") or 0) for s in planned_slots if s.get("action") in EXPORT_PLAN_ACTIONS),
        3,
    )
    spread_profit = round(
        sum(
            float(snap.get("expected_spread_profit_p") or 0)
            for snap in plan_snapshots
            if snap.get("expected_spread_profit_p") is not None
        ),
        2,
    )

    daily_chart = build_daily_chart(
        sessions,
        planned_slots,
        range_start_ms=range_start_ms,
        range_end_ms=range_end_ms,
    )

    daily_economics = collect_daily_economics(
        decision_states, range_start_ms=range_start_ms, range_end_ms=range_end_ms
    )
    how_used = build_how_used(
        daily_economics=daily_economics,
        planned_slots=planned_slots,
        battery_charge_pts=battery_charge_pts,
        grid_export_pts=grid_export_pts,
        range_start_ms=range_start_ms,
        range_end_ms=range_end_ms,
    )
    how_used_summary = _how_used_summary(how_used)

    return {
        "period": period,
        "offset": offset,
        "period_label": period_label,
        "range_start_ms": int(range_start_ms),
        "range_end_ms": int(range_end_ms),
        "fetched_at": dt_util.utcnow().isoformat(),
        "summary": {
            "armed_sessions": len(sessions),
            "import_sessions": sum(1 for s in sessions if s["direction"] == "import"),
            "export_sessions": sum(1 for s in sessions if s["direction"] == "export"),
            "grid_import_kwh_actual": import_actual,
            "grid_import_kwh_planned": import_planned,
            "grid_export_kwh_actual": export_actual,
            "grid_export_kwh_planned": export_planned,
            "battery_charge_kwh": round(sum(s["battery_charge_kwh"] for s in sessions), 3),
            "battery_discharge_kwh": round(sum(s["battery_discharge_kwh"] for s in sessions), 3),
            "theoretical_spread_profit_p": spread_profit,
            "operating_mode": operating_mode,
            "plan_revisions": len(plan_snapshots),
            **how_used_summary,
        },
        "how_used": how_used,
        "sessions": sessions,
        "planned_slots": planned_slots,
        "plan_snapshots": [
            {
                "captured_ms": snap["captured_ms"],
                "operating_mode": snap.get("operating_mode"),
                "grid_gap_kwh": snap.get("grid_gap_kwh"),
                "slot_count": len(snap.get("slots") or []),
            }
            for snap in plan_snapshots
        ],
        "daily_chart": daily_chart,
    }


POWER_KEYS = ("grid_import", "grid_export", "battery_charge", "battery_discharge")
# Short-term (5-minute) statistics are kept ~10 days by default; hourly for much longer.
SHORT_TERM_STATS_DAYS = 10


def power_unit_scale(unit: str | None) -> float:
    """Multiplier converting a power sensor's unit to kW (1.0 when unknown / kW)."""
    unit = (unit or "").strip()
    if unit == "W":
        return 0.001
    if unit == "MW":
        return 1000.0
    return 1.0


def merge_power_series(
    hourly: list[dict[str, float]],
    five_minute: list[dict[str, float]],
    *,
    scale: float = 1.0,
) -> list[dict[str, float]]:
    """Prefer 5-minute points; use hourly means only before the 5-minute data starts."""
    fine = [{"t": p["t"], "v": p["v"] * scale} for p in five_minute]
    cutoff = fine[0]["t"] if fine else float("inf")
    coarse = [{"t": p["t"], "v": p["v"] * scale} for p in hourly if p["t"] < cutoff]
    return sorted(coarse + fine, key=lambda p: p["t"])


async def async_build_smart_charge_analysis(
    hass: HomeAssistant,
    coordinator: Any,
    *,
    period: str = "week",
    offset: int = 0,
) -> dict[str, Any]:
    """Build SmartCharge Analysis from HA recorder for the selected report period.

    Entity lookups happen here on the event loop; every recorder / SQLite read runs in
    the recorder executor (HA forbids database access from the event loop).
    """
    from homeassistant.components.recorder import get_instance

    from .discovery import resolve_entity_id

    entry_id = coordinator.config_entry.entry_id
    if not coordinator.plant.smart_charge.enabled:
        return {"error": "SmartCharge is disabled", "enabled": False}

    start_local, end_local, _can_next = reports_period_bounds(period, offset)
    period_label = reports_period_label(period, offset, now=start_local)

    active_id = find_entry_entity(hass, entry_id, "_smart_charge_active")
    decision_id = find_entry_entity(hass, entry_id, "_smart_charge_decision")
    if not active_id:
        return {
            "error": "Smart charge active sensor not found. Reload the integration.",
            "period_label": period_label,
        }

    entity_map = coordinator.plant.entity_map or {}
    power_ids: dict[str, str | None] = {}
    power_scale: dict[str, float] = {}
    for key in POWER_KEYS:
        eid = resolve_entity_id(hass, entity_map, key, device_id=coordinator.plant.device_id)
        power_ids[key] = eid
        state = hass.states.get(eid) if eid else None
        power_scale[key] = power_unit_scale(
            state.attributes.get("unit_of_measurement") if state is not None else None
        )

    sc = coordinator.plant.smart_charge
    store = getattr(coordinator, "_performance_store", None)

    # Today's row isn't in the finalised daily ledger yet, so pull the live running totals (same source the
    # Performance page uses for "today") to fold into the period savings.
    today_live: dict[str, Any] | None = None
    try:
        from .performance.tick import performance_summary

        today_live = (performance_summary(coordinator) or {}).get("today")
        if today_live is not None:
            # The live "today" carries savings but not energy totals; fill those from analytics.
            analytics = coordinator._read_analytics() or {}
            today_live = {
                **today_live,
                "pv_kwh": today_live.get("pv_kwh") or analytics.get("pv_production_kwh_today") or 0,
                "import_kwh": today_live.get("import_kwh") or analytics.get("load_from_grid_kwh_today") or 0,
                "export_kwh": today_live.get("export_kwh") or analytics.get("pv_to_grid_kwh_today") or 0,
            }
    except Exception as err:  # noqa: BLE001 — report still renders without today's live figures
        _LOGGER.debug("SmartCharge analysis live today summary failed: %s", err)

    def job() -> dict[str, Any]:
        return _build_analysis_sync(
            hass,
            period=period,
            offset=offset,
            period_label=period_label,
            start_local=start_local,
            end_local=end_local,
            active_id=active_id,
            decision_id=decision_id,
            power_ids=power_ids,
            power_scale=power_scale,
            operating_mode=getattr(sc, "operating_mode", None),
            store=store,
            today_live=today_live,
        )

    return await get_instance(hass).async_add_executor_job(job)


def _recorder_states(
    hass: HomeAssistant,
    entity_id: str,
    start_utc: datetime,
    end_utc: datetime,
    *,
    attributes: bool,
) -> list[Any]:
    from homeassistant.components.recorder import history
    from homeassistant.components.recorder.util import session_scope

    with session_scope(hass=hass, read_only=True) as session:
        states_map = history.get_significant_states_with_session(
            hass,
            session,
            start_utc,
            end_utc,
            [entity_id],
            None,
            include_start_time_state=True,
            significant_changes_only=False,
            minimal_response=False,
            no_attributes=not attributes,
        )
    return list(states_map.get(entity_id) or [])


def _build_analysis_sync(
    hass: HomeAssistant,
    *,
    period: str,
    offset: int,
    period_label: str,
    start_local: datetime,
    end_local: datetime,
    active_id: str,
    decision_id: str | None,
    power_ids: dict[str, str | None],
    power_scale: dict[str, float],
    operating_mode: str | None,
    store: Any,
    today_live: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recorder-executor half of the report: all database reads live here."""
    from .websocket_api import _fetch_statistics_points

    start_utc = dt_util.as_utc(start_local)
    end_utc = dt_util.as_utc(end_local)
    now = dt_util.utcnow()
    fetch_end = min(end_utc, now)
    range_start_ms = start_local.timestamp() * 1000
    range_end_ms = min(end_local.timestamp() * 1000, now.timestamp() * 1000)
    history_start = start_utc - timedelta(hours=1)

    decision_states = (
        _recorder_states(hass, decision_id, history_start, fetch_end, attributes=True)
        if decision_id
        else []
    )
    armed_states = _recorder_states(hass, active_id, history_start, fetch_end, attributes=False)

    armed_periods = pair_binary_on_periods(armed_states, range_end_ms=range_end_ms)
    armed_periods = [
        p
        for p in armed_periods
        if p["end_ms"] > range_start_ms and p["start_ms"] < range_end_ms
    ]

    stat_ids = [eid for eid in power_ids.values() if eid]
    power_pts: dict[str, list[dict[str, float]]] = {k: [] for k in power_ids}
    missing_power = [key for key, eid in power_ids.items() if not eid]
    if stat_ids:
        try:
            hourly = _fetch_statistics_points(
                hass, start_utc, fetch_end, stat_ids, period="hour", statistic="mean"
            )
            fine_start = max(start_utc, fetch_end - timedelta(days=SHORT_TERM_STATS_DAYS))
            five_min = (
                _fetch_statistics_points(
                    hass, fine_start, fetch_end, stat_ids, period="5minute", statistic="mean"
                )
                if fine_start < fetch_end
                else {}
            )
            for key, eid in power_ids.items():
                if not eid:
                    continue
                power_pts[key] = merge_power_series(
                    stats_rows_to_power_points(hourly.get(eid) or []),
                    stats_rows_to_power_points(five_min.get(eid) or []),
                    scale=power_scale.get(key, 1.0),
                )
        except Exception as err:  # noqa: BLE001 — report still renders sessions without energy
            _LOGGER.warning("SmartCharge analysis statistics failed: %s", err)

    plan_snapshots = collect_plan_snapshots(
        decision_states,
        range_start_ms=range_start_ms,
        range_end_ms=range_end_ms,
    )

    payload = build_smart_charge_analysis_payload(
        period=period,
        offset=offset,
        period_label=period_label,
        range_start_ms=range_start_ms,
        range_end_ms=range_end_ms,
        armed_periods=armed_periods,
        decision_states=decision_states,
        grid_import_pts=power_pts["grid_import"],
        grid_export_pts=power_pts["grid_export"],
        battery_charge_pts=power_pts["battery_charge"],
        battery_discharge_pts=power_pts["battery_discharge"],
        plan_snapshots=plan_snapshots,
        operating_mode=operating_mode,
    )
    if missing_power:
        payload["power_sensors_missing"] = missing_power
    if not armed_periods and not plan_snapshots:
        payload["hint"] = (
            "No SmartCharge activity recorded for this period. "
            "Armed sessions and daily plans are stored when the recorder keeps history "
            "for the smart charge sensors."
        )
    elif missing_power:
        payload["hint"] = (
            "Some power sensors could not be found ("
            + ", ".join(k.replace("_", " ") for k in missing_power)
            + ") — their energy totals show as 0."
        )
    if store is not None:
        from .performance.hems_audit import build_hems_audit_report

        start_date = dt_util.as_local(start_local).date().isoformat()
        end_date = dt_util.as_local(end_local).date().isoformat()
        payload["hems_audit"] = build_hems_audit_report(store, start_date=start_date, end_date=end_date)
        # Whole-system saving vs having no PV/battery (buy everything from the grid): avoided import +
        # export earnings, from the performance ledger, per day and summed. Today isn't finalised in the
        # ledger yet, so fold in the live running totals so the current week isn't all zeros.
        try:
            today_iso = dt_util.as_local(dt_util.utcnow()).date().isoformat()
            daily: dict[str, dict[str, Any]] = {}
            for row in store.list_ledger_between(start_date, end_date):
                daily[str(row.get("date"))] = _system_day_row(row)
            if today_live and start_date <= today_iso <= end_date:
                daily[today_iso] = _system_day_row({**today_live, "date": today_iso})
            system_daily = [daily[k] for k in sorted(daily)]
            payload["system_daily"] = system_daily
            payload["system_savings"] = _system_savings_totals(system_daily)
        except Exception as err:  # noqa: BLE001 — report still renders without it
            _LOGGER.debug("SmartCharge analysis system savings aggregate failed: %s", err)
    return payload


def _system_day_row(row: dict[str, Any]) -> dict[str, Any]:
    def num(key: str) -> float:
        try:
            return round(float(row.get(key) or 0), 3)
        except (TypeError, ValueError):
            return 0.0

    return {
        "date": str(row.get("date")),
        "net_saving_gbp": num("net_daily_savings_gbp"),
        "avoided_grid_cost_gbp": num("avoided_grid_cost_gbp"),
        "export_earnings_gbp": num("export_earnings_gbp"),
        "pv_kwh": num("pv_kwh"),
        "import_kwh": num("import_kwh"),
        "export_kwh": num("export_kwh"),
    }


def _system_savings_totals(system_daily: list[dict[str, Any]]) -> dict[str, Any]:
    def total(key: str) -> float:
        return round(sum(float(r.get(key) or 0) for r in system_daily), 2)

    return {
        "net_daily_savings_gbp": total("net_saving_gbp"),
        "avoided_grid_cost_gbp": total("avoided_grid_cost_gbp"),
        "export_earnings_gbp": total("export_earnings_gbp"),
        "pv_kwh": round(sum(float(r.get("pv_kwh") or 0) for r in system_daily), 2),
        "import_kwh": round(sum(float(r.get("import_kwh") or 0) for r in system_daily), 2),
        "export_kwh": round(sum(float(r.get("export_kwh") or 0) for r in system_daily), 2),
        "days": len(system_daily),
    }


__all__ = [
    "async_build_smart_charge_analysis",
    "build_how_used",
    "build_smart_charge_analysis_payload",
    "collect_daily_economics",
    "integrate_power_kwh",
    "merge_power_series",
    "pair_binary_on_periods",
    "power_unit_scale",
    "reports_period_bounds",
    "reports_period_label",
    "resolve_slot_range_ms",
]
