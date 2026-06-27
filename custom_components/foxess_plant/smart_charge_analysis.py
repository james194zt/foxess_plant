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
    clipped = [p for p in points if start_ms <= p["t"] <= end_ms]
    if not clipped:
        before = [p for p in points if p["t"] < start_ms]
        after = [p for p in points if p["t"] > end_ms]
        if not before:
            return 0.0
        v0 = before[-1]["v"]
        v1 = after[0]["v"] if after else v0
        hours = (end_ms - start_ms) / 3_600_000
        return max(0.0, ((v0 + v1) / 2) * hours)
    seq = list(clipped)
    before = [p for p in points if p["t"] < start_ms]
    if before and seq[0]["t"] > start_ms:
        seq.insert(0, {"t": start_ms, "v": before[-1]["v"]})
    after = [p for p in points if p["t"] > end_ms]
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
        hours = (t1 - t0) / 3_600_000
        total += ((v0 + v1) / 2) * hours
    return round(total, 3)


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
        anchor = dt_util.as_local(dt_util.utc_from_timestamp(t_ms / 1000))
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
        d = dt_util.as_local(dt_util.utc_from_timestamp(ms / 1000))
        return d.strftime("%Y-%m-%d")

    cursor = dt_util.as_local(dt_util.utc_from_timestamp(range_start_ms / 1000)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end_local = dt_util.as_local(dt_util.utc_from_timestamp(range_end_ms / 1000))
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
        },
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


async def async_build_smart_charge_analysis(
    hass: HomeAssistant,
    coordinator: Any,
    *,
    period: str = "week",
    offset: int = 0,
) -> dict[str, Any]:
    """Build SmartCharge Analysis from HA recorder for the selected report period."""
    from .websocket_api import _fetch_statistics_points

    entry_id = coordinator.config_entry.entry_id
    if not coordinator.plant.smart_charge.enabled:
        return {"error": "SmartCharge is disabled", "enabled": False}

    start_local, end_local, _can_next = reports_period_bounds(period, offset)
    start_utc = dt_util.as_utc(start_local)
    end_utc = dt_util.as_utc(end_local)
    now = dt_util.utcnow()
    fetch_end = min(end_utc, now)
    range_start_ms = start_local.timestamp() * 1000
    range_end_ms = min(end_local.timestamp() * 1000, now.timestamp() * 1000)
    period_label = reports_period_label(period, offset, now=start_local)

    active_id = find_entry_entity(hass, entry_id, "_smart_charge_active")
    decision_id = find_entry_entity(hass, entry_id, "_smart_charge_decision")
    entity_map = coordinator.plant.entity_map or {}
    power_keys = {
        "grid_import": "grid_import",
        "grid_export": "feed_in",
        "battery_charge": "battery_charge",
        "battery_discharge": "battery_discharge",
    }
    power_ids: dict[str, str | None] = {
        key: entity_map.get(map_key) for key, map_key in power_keys.items()
    }

    if not active_id:
        return {
            "error": "Smart charge active sensor not found. Reload the integration.",
            "period_label": period_label,
        }

    decision_states: list[Any] = []
    if decision_id:
        from homeassistant.components.recorder import history
        from homeassistant.components.recorder.util import session_scope

        with session_scope(hass=hass, read_only=True) as session:
            states_map = history.get_significant_states_with_session(
                hass,
                session,
                start_utc - timedelta(hours=1),
                fetch_end,
                [decision_id],
                None,
                include_start_time_state=True,
                significant_changes_only=False,
                minimal_response=False,
                no_attributes=False,
            )
        decision_states = list(states_map.get(decision_id) or [])

    armed_states: list[Any] = []
    from homeassistant.components.recorder import history
    from homeassistant.components.recorder.util import session_scope

    with session_scope(hass=hass, read_only=True) as session:
        active_map = history.get_significant_states_with_session(
            hass,
            session,
            start_utc - timedelta(hours=1),
            fetch_end,
            [active_id],
            None,
            include_start_time_state=True,
            significant_changes_only=False,
            minimal_response=False,
            no_attributes=True,
        )
    armed_states = list(active_map.get(active_id) or [])

    armed_periods = pair_binary_on_periods(armed_states, range_end_ms=range_end_ms)
    armed_periods = [
        p
        for p in armed_periods
        if p["end_ms"] > range_start_ms and p["start_ms"] < range_end_ms
    ]

    stat_ids = [eid for eid in power_ids.values() if eid]
    power_pts: dict[str, list[dict[str, float]]] = {k: [] for k in power_ids}
    if stat_ids:
        try:
            stats = _fetch_statistics_points(hass, start_utc, fetch_end, stat_ids, period="5minute", statistic="mean")
            for key, eid in power_ids.items():
                if eid:
                    power_pts[key] = stats.get(eid) or []
        except Exception as err:
            _LOGGER.warning("SmartCharge analysis statistics failed: %s", err)

    plan_snapshots = collect_plan_snapshots(
        decision_states,
        range_start_ms=range_start_ms,
        range_end_ms=range_end_ms,
    )
    sc = coordinator.plant.smart_charge
    operating_mode = getattr(sc, "operating_mode", None)

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
    if not armed_periods and not plan_snapshots:
        payload["hint"] = (
            "No SmartCharge activity recorded for this period. "
            "Armed sessions and daily plans are stored when the recorder keeps history "
            "for the smart charge sensors."
        )
    return payload


__all__ = [
    "async_build_smart_charge_analysis",
    "build_smart_charge_analysis_payload",
    "integrate_power_kwh",
    "pair_binary_on_periods",
    "reports_period_bounds",
    "reports_period_label",
    "resolve_slot_range_ms",
]
