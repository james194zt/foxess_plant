"""SmartCharge planner — half-hour timeline, battery simulation, cost optimiser.

Pure stdlib (no Home Assistant import) so it can be unit tested directly.

Pipeline:
    build_timeline()  -> list[Slot]      prices + PV + load on a 30-minute UTC grid
    optimise()        -> list[dict]      greedy cost descent over charge / export moves
    decide()          -> dict            what to do in the slot containing "now"
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, tzinfo
from statistics import median
from typing import Any

SLOT = timedelta(minutes=30)
MAX_HORIZON = timedelta(hours=48)

MODE_MAX_SAFETY = "max_safety"
MODE_MAX_PROFIT = "max_profit"
MODE_MAX_GREEN = "max_green"

ACTION_CHARGE = "charge"
ACTION_EXPORT = "export"
ACTION_IDLE = "idle"


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def parse_iso(value: Any) -> datetime | None:
    """Parse an ISO timestamp (``Z`` allowed) to an aware UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def floor_half_hour(when: datetime) -> datetime:
    when = when.astimezone(timezone.utc)
    return when.replace(minute=0 if when.minute < 30 else 30, second=0, microsecond=0)


def fmt_local(when: datetime, tz: tzinfo) -> str:
    return when.astimezone(tz).strftime("%H:%M")


def default_horizon_end(now: datetime, tz: tzinfo, last_known: datetime | None) -> datetime:
    """End of tomorrow (local), extended to the last known price, capped at 48h."""
    start = floor_half_hour(now)
    local = now.astimezone(tz)
    end_of_tomorrow = (local + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = end_of_tomorrow.astimezone(timezone.utc)
    if last_known is not None and last_known > end:
        end = last_known
    return min(end, start + MAX_HORIZON)


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


@dataclass
class Slot:
    start: datetime
    end: datetime
    import_p: float
    export_p: float
    pv_kwh: float
    load_kwh: float
    price_known: bool = True
    carbon_score: float | None = None  # 1 (dirty) .. 10 (green)
    hours: float = 0.5  # effective duration (first slot may be partial)


def _rate_intervals(rows: list[dict[str, Any]] | None, open_end: datetime) -> list[tuple[datetime, datetime, float]]:
    out: list[tuple[datetime, datetime, float]] = []
    for row in rows or []:
        start = parse_iso(row.get("valid_from"))
        if start is None:
            continue
        end = parse_iso(row.get("valid_to")) or open_end
        try:
            value = float(row.get("value_inc_vat"))
        except (TypeError, ValueError):
            continue
        if end > start:
            out.append((start, end, value))
    # Later-starting rows win when rows overlap (e.g. open-ended old row + new row).
    out.sort(key=lambda r: r[0])
    return out


def _rate_for(intervals: list[tuple[datetime, datetime, float]], when: datetime) -> float | None:
    found: float | None = None
    for start, end, value in intervals:
        if start > when:
            break
        if start <= when < end:
            found = value
    return found


def last_known_rate_end(rows: list[dict[str, Any]] | None) -> datetime | None:
    ends = [parse_iso(r.get("valid_to")) for r in rows or []]
    ends = [e for e in ends if e is not None]
    return max(ends) if ends else None


def _pv_intervals(forecast_rows: list[dict[str, Any]] | None) -> list[tuple[datetime, datetime, float]]:
    """(start, end, kW) intervals from Solcast rows.

    Solcast reports each value at the END of its period. Fox Plant's merged rows carry
    ``period_start == period_end`` (both the end time); those are treated as period ends.
    """
    parsed: list[tuple[datetime, float, bool]] = []
    for row in forecast_rows or []:
        start = parse_iso(row.get("period_start"))
        end = parse_iso(row.get("period_end"))
        is_end = end is not None and (start is None or start == end)
        when = end if is_end else start
        if when is None:
            continue
        try:
            kw = float(row.get("pv_estimate"))
        except (TypeError, ValueError):
            continue
        parsed.append((when, max(0.0, kw), is_end))
    parsed.sort(key=lambda r: r[0])
    out: list[tuple[datetime, datetime, float]] = []
    for i, (when, kw, is_end) in enumerate(parsed):
        if is_end:
            length = SLOT
            if i > 0 and parsed[i - 1][0] < when:
                length = min(when - parsed[i - 1][0], timedelta(hours=1))
            out.append((when - length, when, kw))
        else:
            end = when + SLOT
            if i + 1 < len(parsed) and parsed[i + 1][0] > when:
                end = min(parsed[i + 1][0], when + timedelta(hours=1))
            out.append((when, end, kw))
    return out


def forecast_end(forecast_rows: list[dict[str, Any]] | None) -> datetime | None:
    intervals = _pv_intervals(forecast_rows)
    return max((e for _s, e, _kw in intervals), default=None)


def _row_time(row: dict[str, Any]) -> datetime | None:
    return parse_iso(row.get("period_end")) or parse_iso(row.get("period_start"))


def merge_forecast_snapshots(
    snapshots: list[list[dict[str, Any]] | None],
    *,
    now: datetime,
    keep: timedelta = timedelta(days=2),
) -> list[dict[str, Any]]:
    """Union of Solcast polls (oldest first); the newest poll wins for each period.

    A single poll only covers from its fetch time onwards, and the latest stored poll
    may not reach tomorrow. Older polls fill those gaps. Rows older than ``keep`` are
    dropped — they only matter as a same-time-yesterday source for estimates.
    """
    cutoff = now - keep
    by_time: dict[datetime, dict[str, Any]] = {}
    for rows in snapshots:
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            when = _row_time(row)
            if when is None or when < cutoff:
                continue
            by_time[when] = row
    return [by_time[k] for k in sorted(by_time)]


def fill_missing_pv(
    forecast_rows: list[dict[str, Any]] | None,
    *,
    now: datetime,
    tz: tzinfo,
    until: datetime,
    lookback_days: int = 3,
) -> list[dict[str, Any]]:
    """Extend a forecast that stops short of ``until`` with same-time-previous-day values.

    Without this, an unknown tomorrow means 0 kWh PV and the planner grid-charges for
    solar that will probably arrive. Added rows carry ``estimated: True``.
    """
    rows = [r for r in (forecast_rows or []) if isinstance(r, dict)]
    end = forecast_end(rows)
    if end is None or end >= until:
        return rows
    by_local: dict[datetime, float] = {}
    for s, e, kw in _pv_intervals(rows):
        by_local[e.astimezone(tz)] = kw
    added: list[dict[str, Any]] = []
    cursor = floor_half_hour(end.astimezone(timezone.utc))
    if cursor < end:
        cursor += SLOT
    while cursor <= until:
        target = cursor.astimezone(tz)
        kw = 0.0
        for back in range(1, lookback_days + 1):
            # Aware local arithmetic keeps wall-clock time across DST changes.
            source = by_local.get((target - timedelta(days=back)).astimezone(tz))
            if source is not None:
                kw = source
                break
        iso = cursor.isoformat()
        added.append({"period_start": iso, "period_end": iso, "pv_estimate": kw, "estimated": True})
        cursor += SLOT
    return rows + added


def _overlap_kwh(intervals: list[tuple[datetime, datetime, float]], start: datetime, end: datetime) -> float:
    total = 0.0
    for s, e, kw in intervals:
        if e <= start or s >= end:
            continue
        overlap = (min(e, end) - max(s, start)).total_seconds() / 3600.0
        total += kw * overlap
    return total


def load_for_slot(profile: dict[str, Any] | None, start: datetime, tz: tzinfo, fallback_kw: float) -> float:
    """Expected house load (kWh) for the half-hour starting at ``start``."""
    fallback = max(0.0, fallback_kw) * 0.5
    if not profile:
        return fallback
    local = start.astimezone(tz)
    idx = local.hour * 2 + (1 if local.minute >= 30 else 0)
    key = "weekend" if local.weekday() >= 5 else "weekday"
    values = profile.get(key) or profile.get("all")
    if not isinstance(values, list) or len(values) != 48:
        return fallback
    try:
        return max(0.0, float(values[idx]))
    except (TypeError, ValueError):
        return fallback


def _carbon_for(periods: list[dict[str, Any]] | None, when: datetime) -> float | None:
    if not periods:
        return None
    ms = int(when.timestamp() * 1000)
    for row in periods:
        s, e = row.get("start_ms"), row.get("end_ms")
        if s is None or e is None:
            continue
        if int(s) <= ms < int(e):
            score = row.get("low_carbon_score")
            return float(score) if score is not None else None
    return None


def build_timeline(
    *,
    now: datetime,
    tz: tzinfo,
    import_rows: list[dict[str, Any]] | None,
    export_rows: list[dict[str, Any]] | None = None,
    forecast_rows: list[dict[str, Any]] | None = None,
    load_profile: dict[str, Any] | None = None,
    load_fallback_kw: float = 0.5,
    carbon_periods: list[dict[str, Any]] | None = None,
    horizon_end: datetime | None = None,
    default_export_p: float = 0.0,
) -> list[Slot]:
    """Normalise rates / PV / load onto a strict 30-minute UTC grid starting now."""
    now = now.astimezone(timezone.utc)
    start = floor_half_hour(now)
    end = horizon_end or default_horizon_end(now, tz, last_known_rate_end(import_rows))
    imp = _rate_intervals(import_rows, end)
    exp = _rate_intervals(export_rows, end)
    pv = _pv_intervals(forecast_rows)

    starts: list[datetime] = []
    cursor = start
    while cursor < end:
        starts.append(cursor)
        cursor += SLOT

    raw_imp = [_rate_for(imp, s) for s in starts]
    raw_exp = [_rate_for(exp, s) for s in starts]
    known_imp = [p for p in raw_imp if p is not None]
    known_exp = [p for p in raw_exp if p is not None]
    est_imp = median(known_imp) if known_imp else 0.0
    est_exp = median(known_exp) if known_exp else default_export_p

    slots: list[Slot] = []
    for i, s in enumerate(starts):
        e = s + SLOT
        eff_start = max(s, now)
        hours = max(0.0, (e - eff_start).total_seconds() / 3600.0)
        frac = hours / 0.5 if hours else 0.0
        slots.append(
            Slot(
                start=s,
                end=e,
                import_p=raw_imp[i] if raw_imp[i] is not None else est_imp,
                export_p=raw_exp[i] if raw_exp[i] is not None else est_exp,
                pv_kwh=_overlap_kwh(pv, eff_start, e),
                load_kwh=load_for_slot(load_profile, s, tz, load_fallback_kw) * frac,
                price_known=raw_imp[i] is not None,
                carbon_score=_carbon_for(carbon_periods, s),
                hours=hours,
            )
        )
    return [s for s in slots if s.hours > 0]


def schedule_rate_rows(
    rate_at: Any,
    *,
    now: datetime,
    tz: tzinfo,
    horizon: timedelta = MAX_HORIZON,
    key: str = "import_p_per_kwh",
) -> list[dict[str, Any]]:
    """Sample a manual schedule (``rate_at(local_dt) -> dict``) into half-hour rate rows."""
    rows: list[dict[str, Any]] = []
    cursor = floor_half_hour(now)
    end = cursor + horizon
    while cursor < end:
        rates = rate_at(cursor.astimezone(tz)) or {}
        try:
            value = float(rates.get(key) or 0.0)
        except (TypeError, ValueError):
            value = 0.0
        rows.append(
            {
                "valid_from": cursor.isoformat(),
                "valid_to": (cursor + SLOT).isoformat(),
                "value_inc_vat": value,
            }
        )
        cursor += SLOT
    return rows


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


@dataclass
class PlanParams:
    capacity_kwh: float
    floor_kwh: float  # self-use never drains below this
    cap_kwh: float  # grid charge / PV never fills above this
    charge_kw: float = 3.0
    discharge_kw: float = 3.0
    round_trip_efficiency: float = 0.9
    pv_scale: float = 1.0
    load_scale: float = 1.0
    export_allowed: bool = True
    min_export_p: float = 0.0
    export_floor_kwh: float = 0.0  # forced export never drains below this
    max_export_kwh: float | None = None  # forced export budget per local day
    carbon_weight_p: float = 0.0  # pence-equivalent per kWh per dirty point
    min_saving_p_per_kwh: float = 1.0
    terminal_p_per_kwh: float | None = None  # value of energy left at horizon end

    @property
    def eff_one_way(self) -> float:
        return math.sqrt(max(0.1, min(1.0, self.round_trip_efficiency)))


def _cfg(config: Any, key: str, default: float) -> float:
    try:
        value = getattr(config, key, default)
        return float(default if value is None else value)
    except (TypeError, ValueError):
        return default


def params_from_config(
    config: Any,
    *,
    capacity_kwh: float,
    reserve_kwh: float,
    inverter_min_soc_pct: float | None = None,
) -> PlanParams:
    """Map SmartCharge config + operating mode onto planner parameters."""
    mode = str(getattr(config, "operating_mode", MODE_MAX_SAFETY) or MODE_MAX_SAFETY)
    cap_pct = min(100.0, max(10.0, _cfg(config, "max_target_soc", 100.0)))
    min_soc_kwh = capacity_kwh * max(0.0, inverter_min_soc_pct or 0.0) / 100.0
    floor = min(capacity_kwh * cap_pct / 100.0, max(min_soc_kwh, reserve_kwh))
    export_floor = max(floor, capacity_kwh * max(0.0, _cfg(config, "export_min_soc", 40.0)) / 100.0)
    charge_kw = max(0.1, _cfg(config, "max_charge_kw", 3.0))
    discharge_kw = max(0.1, _cfg(config, "max_discharge_kw", 0.0) or charge_kw)

    export_on = bool(getattr(config, "export_enabled", True))
    if mode == MODE_MAX_PROFIT:
        min_export_p = _cfg(config, "min_export_p_profit", 12.0)
        fraction = _cfg(config, "exportable_fraction_profit", 1.0)
        pv_scale, load_scale, carbon_w = 1.0, 1.0, 0.0
    elif mode == MODE_MAX_GREEN:
        export_on = export_on and bool(getattr(config, "export_enabled_green", False))
        min_export_p = _cfg(config, "min_export_p_green", 25.0)
        fraction = _cfg(config, "exportable_fraction_green", 0.15)
        pv_scale, load_scale = 1.0, 1.0
        carbon_w = max(0.0, min(1.0, _cfg(config, "green_carbon_weight", 0.5)))
    else:
        export_on = export_on and bool(getattr(config, "export_enabled_safety", True))
        min_export_p = _cfg(config, "min_export_p_safety", 20.0)
        fraction = _cfg(config, "exportable_fraction_safety", 0.35)
        pv_scale = 1.0 / max(1.0, _cfg(config, "solar_safety_margin", 1.15))
        load_scale, carbon_w = 1.1, 0.0

    cap_kwh = capacity_kwh * cap_pct / 100.0
    return PlanParams(
        capacity_kwh=capacity_kwh,
        floor_kwh=floor,
        cap_kwh=cap_kwh,
        charge_kw=charge_kw,
        discharge_kw=discharge_kw,
        round_trip_efficiency=_cfg(config, "round_trip_efficiency", 0.9),
        pv_scale=pv_scale,
        load_scale=load_scale,
        export_allowed=export_on,
        min_export_p=min_export_p,
        export_floor_kwh=export_floor,
        max_export_kwh=max(0.0, min(1.0, fraction)) * max(0.0, cap_kwh - export_floor),
        carbon_weight_p=carbon_w,
        min_saving_p_per_kwh=max(0.0, _cfg(config, "min_saving_p_per_kwh", 1.0)),
    )


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


@dataclass
class SimResult:
    cost_p: float
    soc_kwh: list[float]  # SOC at end of each slot
    grid_import: list[float]
    grid_export: list[float]
    charged: list[float]  # grid kWh actually used for forced charge
    discharged: list[float]  # battery kWh actually removed by forced export


def _terminal_value(slots: list[Slot], params: PlanParams) -> float:
    if params.terminal_p_per_kwh is not None:
        return params.terminal_p_per_kwh
    prices = [s.import_p for s in slots]
    return max(0.0, median(prices)) * params.eff_one_way if prices else 0.0


def simulate(
    slots: list[Slot],
    soc0_kwh: float,
    params: PlanParams,
    charge: list[float],
    discharge: list[float],
) -> SimResult:
    eff = params.eff_one_way
    soc = max(0.0, min(params.capacity_kwh, soc0_kwh))
    cost = 0.0
    socs: list[float] = []
    imports: list[float] = []
    exports: list[float] = []
    charged: list[float] = []
    discharged: list[float] = []
    for i, slot in enumerate(slots):
        pv = slot.pv_kwh * params.pv_scale
        load = slot.load_kwh * params.load_scale
        imp = 0.0
        exp = 0.0
        used_c = 0.0
        used_d = 0.0
        net = pv - load
        if charge[i] > 0:
            # Force charge: battery does not feed the house; PV surplus also charges.
            room = max(0.0, params.cap_kwh - soc)
            used_c = min(charge[i], params.charge_kw * slot.hours, room / eff)
            soc += used_c * eff
            imp += used_c
            if net >= 0:
                store = min(net * eff, max(0.0, params.cap_kwh - soc))
                soc += store
                exp += net - store / eff
            else:
                imp += -net
        elif discharge[i] > 0:
            # Force discharge: battery output serves the house first, remainder exported.
            avail = max(0.0, soc - params.export_floor_kwh)
            used_d = min(discharge[i], params.discharge_kw * slot.hours, avail)
            soc -= used_d
            supply = pv + used_d * eff - load
            if supply >= 0:
                exp += supply
            else:
                imp += -supply
        else:
            if net >= 0:
                store = min(net * eff, max(0.0, params.cap_kwh - soc))
                soc += store
                exp += net - store / eff
            else:
                need = -net
                take = min(need / eff, max(0.0, soc - params.floor_kwh), params.discharge_kw * slot.hours / eff)
                soc -= take
                imp += need - take * eff
        cost += imp * slot.import_p - exp * slot.export_p
        if params.carbon_weight_p and slot.carbon_score is not None:
            cost += imp * params.carbon_weight_p * max(0.0, 10.0 - slot.carbon_score)
        socs.append(soc)
        imports.append(imp)
        exports.append(exp)
        charged.append(used_c)
        discharged.append(used_d)
    cost -= max(0.0, soc - params.floor_kwh) * _terminal_value(slots, params)
    return SimResult(cost, socs, imports, exports, charged, discharged)


# ---------------------------------------------------------------------------
# Optimiser
# ---------------------------------------------------------------------------


def is_plunge(slot: Slot) -> bool:
    """Import price is known and negative: always force charge (paid to import)."""
    return slot.price_known and slot.import_p < 0


def _chunk_sizes(room: float) -> list[float]:
    if room <= 0.01:
        return []
    sizes = {round(room, 3)}
    for frac in (0.5, 0.25):
        if room * frac >= 0.2:
            sizes.add(round(room * frac, 3))
    return sorted(sizes, reverse=True)


def _adjacent(amounts: list[float], i: int) -> bool:
    return (i > 0 and amounts[i - 1] > 0) or (i + 1 < len(amounts) and amounts[i + 1] > 0)


def optimise(
    slots: list[Slot],
    soc0_kwh: float,
    params: PlanParams,
    *,
    tz: tzinfo = timezone.utc,
    max_iterations: int = 400,
) -> tuple[list[float], list[float], SimResult]:
    """Greedy cost descent: repeatedly apply the single best charge/export move."""
    n = len(slots)
    # The export budget is per local day, so each evening peak can export to the floor.
    days = [s.start.astimezone(tz).date() for s in slots]
    # Hard plunge rule: every negative-price slot is a full-rate force charge, whatever
    # PV or the minimum saving say. Kept even when the battery has no room, because force
    # charge also stops the battery feeding the house, so the house imports at the paid rate.
    plunge = [is_plunge(s) for s in slots]
    charge = [params.charge_kw * s.hours if p else 0.0 for s, p in zip(slots, plunge)]
    discharge = [0.0] * n
    result = simulate(slots, soc0_kwh, params, charge, discharge)
    if n == 0:
        return charge, discharge, result

    max_import = max(s.import_p for s in slots)
    for _ in range(max_iterations):
        best: tuple[float, str, int, float] | None = None
        exported_by_day: dict[Any, float] = {}
        for day, kwh in zip(days, result.discharged):
            exported_by_day[day] = exported_by_day.get(day, 0.0) + kwh
        for i, slot in enumerate(slots):
            if not slot.price_known:
                continue
            # Charge move — only if something later is more expensive (or price is negative).
            if discharge[i] == 0 and (slot.import_p < max_import or slot.import_p < 0):
                room = params.charge_kw * slot.hours - charge[i]
                for size in _chunk_sizes(room):
                    trial = list(charge)
                    trial[i] += size
                    res = simulate(slots, soc0_kwh, params, trial, discharge)
                    moved = res.charged[i] - result.charged[i]
                    if moved <= 0.01:
                        continue
                    saving = result.cost_p - res.cost_p
                    if saving < params.min_saving_p_per_kwh * moved:
                        continue
                    # Tie-break towards slots next to existing charge: fewer, longer windows.
                    score = saving + (0.25 if _adjacent(charge, i) else 0.0)
                    if best is None or score > best[0]:
                        best = (score, "c", i, size)
            # Export move.
            if (
                params.export_allowed
                and charge[i] == 0
                and slot.export_p >= params.min_export_p
            ):
                room = params.discharge_kw * slot.hours - discharge[i]
                if params.max_export_kwh is not None:
                    room = min(room, params.max_export_kwh - exported_by_day[days[i]])
                for size in _chunk_sizes(room):
                    trial = list(discharge)
                    trial[i] += size
                    res = simulate(slots, soc0_kwh, params, charge, trial)
                    moved = res.discharged[i] - result.discharged[i]
                    if moved <= 0.01:
                        continue
                    saving = result.cost_p - res.cost_p
                    if saving < params.min_saving_p_per_kwh * moved:
                        continue
                    score = saving + (0.25 if _adjacent(discharge, i) else 0.0)
                    if best is None or score > best[0]:
                        best = (score, "d", i, size)
        if best is None:
            break
        _saving, kind, i, size = best
        if kind == "c":
            charge[i] += size
        else:
            discharge[i] += size
        result = simulate(slots, soc0_kwh, params, charge, discharge)
        # Trim requested energy down to what the battery actually accepted.
        charge = [
            c if p else (min(c, u) if c > 0 else 0.0)
            for c, u, p in zip(charge, result.charged, plunge)
        ]
        discharge = [min(d, u) if d > 0 else 0.0 for d, u in zip(discharge, result.discharged)]
        result = simulate(slots, soc0_kwh, params, charge, discharge)
    return charge, discharge, result


# ---------------------------------------------------------------------------
# Plan output
# ---------------------------------------------------------------------------


@dataclass
class PlanSummary:
    grid_charge_kwh: float = 0.0
    export_kwh: float = 0.0
    pv_kwh: float = 0.0
    load_kwh: float = 0.0
    tomorrow_pv_kwh: float = 0.0
    tomorrow_load_kwh: float = 0.0
    cost_p: float = 0.0
    baseline_cost_p: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = {
            "grid_charge_kwh": round(self.grid_charge_kwh, 2),
            "export_kwh": round(self.export_kwh, 2),
            "pv_kwh": round(self.pv_kwh, 2),
            "load_kwh": round(self.load_kwh, 2),
            "tomorrow_pv_kwh": round(self.tomorrow_pv_kwh, 2),
            "tomorrow_load_kwh": round(self.tomorrow_load_kwh, 2),
            "cost_p": round(self.cost_p, 1),
            "baseline_cost_p": round(self.baseline_cost_p, 1),
            "saving_p": round(self.baseline_cost_p - self.cost_p, 1),
        }
        out.update(self.extras)
        return out


def build_plan(
    slots: list[Slot],
    soc0_kwh: float,
    params: PlanParams,
    *,
    tz: tzinfo,
    now: datetime,
) -> tuple[list[dict[str, Any]], PlanSummary]:
    """Optimise and serialise the plan (one dict per half-hour)."""
    charge, discharge, result = optimise(slots, soc0_kwh, params, tz=tz)
    baseline = simulate(slots, soc0_kwh, params, [0.0] * len(slots), [0.0] * len(slots))
    cap = params.capacity_kwh or 1.0
    tomorrow = (now.astimezone(tz) + timedelta(days=1)).date()

    plan: list[dict[str, Any]] = []
    summary = PlanSummary(cost_p=result.cost_p, baseline_cost_p=baseline.cost_p)
    soc_prev = max(0.0, min(params.capacity_kwh, soc0_kwh))
    for i, slot in enumerate(slots):
        pv = slot.pv_kwh * params.pv_scale
        load = slot.load_kwh * params.load_scale
        if is_plunge(slot):
            action = ACTION_CHARGE
            reason = "negative_import"
        elif result.charged[i] > 0.01:
            action = ACTION_CHARGE
            reason = "grid_charge"
        elif result.discharged[i] > 0.01:
            action = ACTION_EXPORT
            reason = "export_peak"
        else:
            action = ACTION_IDLE
            reason = "self_use"
        plan.append(
            {
                "start": fmt_local(slot.start, tz),
                "end": fmt_local(slot.end, tz),
                "start_utc": slot.start.isoformat(),
                "end_utc": slot.end.isoformat(),
                "action": action,
                "reason": reason,
                "import_p_per_kwh": round(slot.import_p, 4),
                "export_p_per_kwh": round(slot.export_p, 4),
                "price_known": slot.price_known,
                "pv_kwh": round(pv, 3),
                "load_kwh": round(load, 3),
                "planned_import_kwh": round(result.charged[i], 3) if action == ACTION_CHARGE else 0.0,
                "planned_export_kwh": round(result.discharged[i], 3) if action == ACTION_EXPORT else 0.0,
                "grid_import_kwh": round(result.grid_import[i], 3),
                "grid_export_kwh": round(result.grid_export[i], 3),
                "soc_start_pct": round(soc_prev / cap * 100.0, 1),
                "soc_end_pct": round(result.soc_kwh[i] / cap * 100.0, 1),
                "carbon_score": slot.carbon_score,
            }
        )
        if action == ACTION_CHARGE and reason == "negative_import":
            # Plunge charges run to the max SOC even if the forecast says the battery is full.
            plan[-1]["target_soc_pct"] = round(params.cap_kwh / cap * 100.0, 1)
        soc_prev = result.soc_kwh[i]
        summary.grid_charge_kwh += result.charged[i]
        summary.export_kwh += result.discharged[i]
        summary.pv_kwh += pv
        summary.load_kwh += load
        if slot.start.astimezone(tz).date() == tomorrow:
            summary.tomorrow_pv_kwh += pv
            summary.tomorrow_load_kwh += load
    return plan, summary


# ---------------------------------------------------------------------------
# Executor — act on the slot containing "now"
# ---------------------------------------------------------------------------


def plan_index_at(plan: list[dict[str, Any]] | None, now: datetime) -> int | None:
    now = now.astimezone(timezone.utc)
    for i, entry in enumerate(plan or []):
        start = parse_iso(entry.get("start_utc"))
        end = parse_iso(entry.get("end_utc"))
        if start is not None and end is not None and start <= now < end:
            return i
    return None


def current_plan_slot(plan: list[dict[str, Any]] | None, now: datetime) -> dict[str, Any] | None:
    idx = plan_index_at(plan, now)
    return plan[idx] if plan and idx is not None else None


def block_around(plan: list[dict[str, Any]], index: int) -> tuple[int, int]:
    """Contiguous run of slots sharing ``plan[index]['action']``."""
    action = plan[index].get("action")
    lo = index
    while lo > 0 and plan[lo - 1].get("action") == action and plan[lo - 1].get("end_utc") == plan[lo].get("start_utc"):
        lo -= 1
    hi = index
    while (
        hi + 1 < len(plan)
        and plan[hi + 1].get("action") == action
        and plan[hi + 1].get("start_utc") == plan[hi].get("end_utc")
    ):
        hi += 1
    return lo, hi


def next_block(plan: list[dict[str, Any]], after: int, action: str) -> tuple[int, int] | None:
    for i in range(after + 1, len(plan)):
        if plan[i].get("action") == action:
            return block_around(plan, i)
    return None


def _block_window(plan: list[dict[str, Any]], lo: int, hi: int, *, kwh_key: str) -> dict[str, Any]:
    prices = [float(plan[k].get("import_p_per_kwh") or 0) for k in range(lo, hi + 1)]
    exports = [float(plan[k].get("export_p_per_kwh") or 0) for k in range(lo, hi + 1)]
    return {
        "start": plan[lo].get("start"),
        "end": plan[hi].get("end"),
        "start_utc": plan[lo].get("start_utc"),
        "end_utc": plan[hi].get("end_utc"),
        "kwh": round(sum(float(plan[k].get(kwh_key) or 0) for k in range(lo, hi + 1)), 2),
        "import_p_per_kwh": round(min(prices), 4) if prices else None,
        "export_p_per_kwh": round(max(exports), 4) if exports else None,
        "soc_end_pct": plan[hi].get("soc_end_pct"),
    }


def expected_soc_pct(plan: list[dict[str, Any]], now: datetime) -> float | None:
    idx = plan_index_at(plan, now)
    if idx is None:
        return None
    entry = plan[idx]
    start = parse_iso(entry.get("start_utc"))
    end = parse_iso(entry.get("end_utc"))
    a = entry.get("soc_start_pct")
    b = entry.get("soc_end_pct")
    if start is None or end is None or a is None or b is None:
        return None
    frac = (now.astimezone(timezone.utc) - start).total_seconds() / max(1.0, (end - start).total_seconds())
    return float(a) + (float(b) - float(a)) * max(0.0, min(1.0, frac))


def decide(plan: list[dict[str, Any]] | None, now: datetime) -> dict[str, Any]:
    """Return the action for ``now`` from a committed plan.

    Keys: action (grid_charge | arbitrage | export_discharge | idle), reason,
    window (dict | None), target_soc_pct, next_charge, next_export.
    """
    plan = plan or []
    idx = plan_index_at(plan, now)
    if idx is None:
        return {"action": "idle", "reason": "No plan slot for current time", "window": None}

    entry = plan[idx]
    nxt_c = next_block(plan, idx, ACTION_CHARGE)
    nxt_e = next_block(plan, idx, ACTION_EXPORT)
    out: dict[str, Any] = {
        "next_charge": _block_window(plan, *nxt_c, kwh_key="planned_import_kwh") if nxt_c else None,
        "next_export": _block_window(plan, *nxt_e, kwh_key="planned_export_kwh") if nxt_e else None,
    }
    action = entry.get("action")
    if action == ACTION_CHARGE:
        lo, hi = block_around(plan, idx)
        window = _block_window(plan, lo, hi, kwh_key="planned_import_kwh")
        target = min(100.0, math.ceil(float(plan[hi].get("soc_end_pct") or 100.0)))
        plunge_cap = [float(plan[j]["target_soc_pct"]) for j in range(lo, hi + 1) if plan[j].get("target_soc_pct")]
        if plunge_cap:
            target = max(target, min(100.0, max(plunge_cap)))
        negative = float(entry.get("import_p_per_kwh") or 0) < 0
        out.update(
            action="arbitrage" if negative else "grid_charge",
            reason=(
                f"{'Negative-price' if negative else 'Planned'} charge {window['start']}-{window['end']} "
                f"({window['kwh']:.1f} kWh to {target:.0f}%)"
            ),
            window=window,
            target_soc_pct=target,
        )
        return out
    if action == ACTION_EXPORT:
        lo, hi = block_around(plan, idx)
        window = _block_window(plan, lo, hi, kwh_key="planned_export_kwh")
        out.update(
            action="export_discharge",
            reason=(
                f"Planned export {window['start']}-{window['end']} "
                f"({window['kwh']:.1f} kWh at {window['export_p_per_kwh']:.1f}p)"
            ),
            window=window,
            target_soc_pct=plan[hi].get("soc_end_pct"),
        )
        return out

    upcoming = []
    if out["next_charge"]:
        w = out["next_charge"]
        upcoming.append(f"next charge {w['start']}-{w['end']} ({w['kwh']:.1f} kWh)")
    if out["next_export"]:
        w = out["next_export"]
        upcoming.append(f"next export {w['start']}-{w['end']} ({w['kwh']:.1f} kWh)")
    out.update(
        action="idle",
        reason="Self use — " + ("; ".join(upcoming) if upcoming else "no grid charge needed"),
        window=None,
    )
    return out


COMPACT_KEYS = (
    "start",
    "end",
    "start_utc",
    "end_utc",
    "action",
    "reason",
    "import_p_per_kwh",
    "export_p_per_kwh",
    "planned_import_kwh",
    "planned_export_kwh",
    "soc_end_pct",
)


def compact_plan(plan: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Action slots only, fewer keys — small enough for recorder attributes."""
    return [
        {k: entry.get(k) for k in COMPACT_KEYS}
        for entry in plan or []
        if entry.get("action") != ACTION_IDLE
    ]


VARIES_THRESHOLD_P = 0.5


def tariff_profile(
    import_rows: list[dict[str, Any]] | None,
    export_rows: list[dict[str, Any]] | None,
    now: datetime,
    *,
    horizon: timedelta = MAX_HORIZON,
) -> dict[str, Any]:
    """Describe the next ``horizon`` of rates so the UI can hide settings that can't matter.

    - ``import_varies`` / ``export_varies``: price moves by at least 0.5p across the window.
    - ``forced_export_useful``: exporting stored energy could beat refilling it later
      (export varies, or the export rate beats the cheapest import).
    """
    start = floor_half_hour(now)
    end = start + horizon
    imp = _rate_intervals(import_rows, end)
    exp = _rate_intervals(export_rows, end)
    imports: list[float] = []
    exports: list[float] = []
    cursor = start
    while cursor < end:
        p = _rate_for(imp, cursor)
        if p is not None:
            imports.append(p)
        e = _rate_for(exp, cursor)
        if e is not None:
            exports.append(e)
        cursor += SLOT
    out: dict[str, Any] = {"import_known": bool(imports), "export_known": bool(exports)}
    if imports:
        out.update(
            import_min_p=round(min(imports), 2),
            import_max_p=round(max(imports), 2),
            import_varies=max(imports) - min(imports) >= VARIES_THRESHOLD_P,
        )
    has_export = bool(exports) and max(exports) > 0
    out["has_export"] = has_export
    if exports:
        out.update(
            export_min_p=round(min(exports), 2),
            export_max_p=round(max(exports), 2),
            export_varies=max(exports) - min(exports) >= VARIES_THRESHOLD_P,
        )
    out["forced_export_useful"] = bool(
        has_export
        and (
            out.get("export_varies")
            or (imports and max(exports) > min(imports))
        )
    )
    return out


def plan_rates_signature(rows: list[dict[str, Any]] | None, now: datetime) -> str:
    """Signature of future import prices — changes when rates are published or revised."""
    now = now.astimezone(timezone.utc)
    parts: list[str] = []
    for row in rows or []:
        end = parse_iso(row.get("valid_to"))
        if end is not None and end <= now:
            continue
        parts.append(f"{row.get('valid_from')}={row.get('value_inc_vat')}")
    parts.sort()
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]
