"""SmartCharge HEMS audit trail — SQLite hems_events logging and report."""

from __future__ import annotations

import hashlib
import json
from typing import Any

EVENT_DAILY_PLAN = "smart_charge_daily_plan"
EVENT_PLUNGE_OVERRIDE = "smart_charge_plunge_override"
EVENT_EXPORT_ARMED = "smart_charge_export_armed"
EVENT_SPREAD_PAIRS = "smart_charge_spread_pairs"

EVENT_LABELS = {
    EVENT_DAILY_PLAN: "Daily plan",
    EVENT_PLUNGE_OVERRIDE: "Plunge override",
    EVENT_EXPORT_ARMED: "Export armed",
    EVENT_SPREAD_PAIRS: "Spread pairs",
}


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str, separators=(",", ":"))


def daily_plan_signature(plan: list[dict[str, Any]] | None) -> str:
    slots = plan or []
    parts: list[str] = []
    for slot in slots[:48]:
        parts.append(
            "|".join(
                str(slot.get(k) or "")
                for k in ("action", "start", "end", "reason", "import_p_per_kwh", "export_p_per_kwh")
            )
        )
    head = slots[0] if slots else {}
    pairs = head.get("spread_pairs") if isinstance(head, dict) else None
    pair_sig = ""
    if isinstance(pairs, list) and pairs:
        pair_sig = ";".join(
            f"{p.get('charge_start')}->{p.get('export_start')}:{p.get('spread_p_per_kwh')}"
            for p in pairs[:12]
        )
    raw = f"{len(slots)}:{';'.join(parts)}:{pair_sig}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def spread_pairs_signature(pairs: list[dict[str, Any]] | None) -> str:
    if not pairs:
        return ""
    return ";".join(
        f"{p.get('charge_start')}->{p.get('export_start')}:{p.get('spread_p_per_kwh')}"
        for p in pairs[:24]
    )


def export_armed_signature(decision: Any) -> str:
    window = None
    if hasattr(decision, "discharge_window"):
        window = decision.discharge_window
    elif isinstance(decision, dict):
        window = decision.get("discharge_window")
    if not window and hasattr(decision, "windows"):
        wins = decision.windows
        window = wins[0] if wins else None
    elif isinstance(decision, dict) and not window:
        wins = decision.get("windows") or []
        window = wins[0] if wins else None
    if not window:
        return ""
    return (
        f"{window.get('start')}|{window.get('end')}|"
        f"{window.get('export_p_per_kwh')}"
    )


def plunge_signature(decision: Any) -> str:
    windows = decision.windows if hasattr(decision, "windows") else (decision.get("windows") or [])
    if not windows:
        reason = decision.reason if hasattr(decision, "reason") else decision.get("reason", "")
        return str(reason)
    w = windows[0]
    return f"{w.get('start')}|{w.get('end')}|{w.get('import_p_per_kwh')}"


def payload_daily_plan(
    plan: list[dict[str, Any]] | None,
    *,
    horizon_hours: float,
    operating_mode: str | None,
) -> dict[str, Any]:
    slots = plan or []
    export_count = sum(1 for s in slots if str(s.get("action") or "") in ("export", "spread_export"))
    charge_count = sum(
        1
        for s in slots
        if str(s.get("action") or "")
        in ("charge", "spread_charge", "winter_fill", "solar_gap_fill", "charge_candidate", "arbitrage")
    )
    head = slots[0] if slots else {}
    pairs = head.get("spread_pairs") if isinstance(head, dict) else []
    return {
        "horizon_hours": horizon_hours,
        "operating_mode": operating_mode,
        "slot_count": len(slots),
        "export_slots": export_count,
        "charge_slots": charge_count,
        "spread_pair_count": len(pairs) if isinstance(pairs, list) else 0,
        "slots": [
            {
                "action": s.get("action"),
                "start": s.get("start"),
                "end": s.get("end"),
                "reason": s.get("reason"),
            }
            for s in slots[:24]
        ],
    }


def payload_plunge_override(decision: Any) -> dict[str, Any]:
    windows = decision.windows if hasattr(decision, "windows") else (decision.get("windows") or [])
    w = windows[0] if windows else {}
    return {
        "reason": decision.reason if hasattr(decision, "reason") else decision.get("reason"),
        "eval_tier": decision.eval_tier if hasattr(decision, "eval_tier") else decision.get("eval_tier"),
        "window": w,
        "target_max_soc": decision.target_max_soc if hasattr(decision, "target_max_soc") else decision.get("target_max_soc"),
    }


def payload_export_armed(decision: Any) -> dict[str, Any]:
    window = None
    if hasattr(decision, "discharge_window"):
        window = decision.discharge_window
    elif isinstance(decision, dict):
        window = decision.get("discharge_window")
    if not window:
        wins = decision.windows if hasattr(decision, "windows") else (decision.get("windows") or [])
        window = wins[0] if wins else None
    return {
        "reason": decision.reason if hasattr(decision, "reason") else decision.get("reason"),
        "action": decision.action if hasattr(decision, "action") else decision.get("action"),
        "discharge_window": window,
        "planned_export_kwh": (
            decision.planned_export_kwh
            if hasattr(decision, "planned_export_kwh")
            else decision.get("planned_export_kwh")
        ),
        "exportable_kwh": (
            decision.exportable_kwh if hasattr(decision, "exportable_kwh") else decision.get("exportable_kwh")
        ),
    }


def payload_spread_pairs(
    pairs: list[dict[str, Any]],
    *,
    profit_p: float | None = None,
) -> dict[str, Any]:
    return {
        "pair_count": len(pairs),
        "expected_spread_profit_p": profit_p,
        "pairs": pairs[:12],
    }


def maybe_log_hems_event(
    coordinator: Any,
    event_type: str,
    payload: dict[str, Any],
    signature: str,
) -> None:
    """Log once per unique signature per event type (avoids 15-min poll spam)."""
    from .tick import log_hems_event

    if not signature:
        return
    sigs: dict[str, str] = getattr(coordinator, "_hems_audit_sigs", None) or {}
    key = f"{event_type}:{signature}"
    if sigs.get(event_type) == signature:
        return
    sigs[event_type] = signature
    coordinator._hems_audit_sigs = sigs
    log_hems_event(coordinator, event_type, payload)


def _format_ts_label(ts: str | None) -> str | None:
    if not ts:
        return None
    try:
        from homeassistant.util import dt as dt_util

        return dt_util.as_local(dt_util.parse_datetime(str(ts))).strftime("%d %b %H:%M")
    except Exception:
        raw = str(ts)
        return raw.replace("T", " ")[:16] if "T" in raw else raw


def _format_event_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload")
    if payload is None and row.get("payload_json"):
        try:
            payload = json.loads(row["payload_json"])
        except (json.JSONDecodeError, TypeError):
            payload = {"raw": row.get("payload_json")}
    ts = row.get("ts")
    local_label = _format_ts_label(str(ts) if ts else None)
    event_type = str(row.get("event_type") or "")
    return {
        "id": row.get("id"),
        "ts": ts,
        "local_label": local_label,
        "event_type": event_type,
        "event_label": EVENT_LABELS.get(event_type, event_type),
        "payload": payload if isinstance(payload, dict) else {},
        "summary": _event_summary(event_type, payload if isinstance(payload, dict) else {}),
    }


def _event_summary(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == EVENT_DAILY_PLAN:
        return (
            f"{payload.get('slot_count', 0)} slots · "
            f"{payload.get('charge_slots', 0)} charge · {payload.get('export_slots', 0)} export"
        )
    if event_type == EVENT_PLUNGE_OVERRIDE:
        w = payload.get("window") or {}
        imp = w.get("import_p_per_kwh")
        if imp is not None:
            return f"Negative import {float(imp):.2f}p/kWh"
        return str(payload.get("reason") or "Plunge")
    if event_type == EVENT_EXPORT_ARMED:
        w = payload.get("discharge_window") or {}
        exp = w.get("export_p_per_kwh")
        start = w.get("start") or "?"
        return f"Export at {start}" + (f" ({exp:.1f}p)" if exp is not None else "")
    if event_type == EVENT_SPREAD_PAIRS:
        return f"{payload.get('pair_count', 0)} pairs · +{payload.get('expected_spread_profit_p', 0):.1f}p theoretical"
    return ""


def build_hems_audit_report(
    store: Any,
    *,
    start_date: str,
    end_date: str,
    limit: int = 200,
) -> dict[str, Any]:
    """Timeline of HEMS audit events for a report period."""
    start_ts = f"{start_date}T00:00:00"
    end_ts = f"{end_date}T23:59:59"
    rows = store.list_events_between(start_ts, end_ts, limit=limit)
    events = [_format_event_row(row) for row in rows]
    by_type: dict[str, int] = {}
    for ev in events:
        by_type[ev["event_type"]] = by_type.get(ev["event_type"], 0) + 1
    return {
        "start_date": start_date,
        "end_date": end_date,
        "event_count": len(events),
        "by_type": by_type,
        "events": events,
    }
