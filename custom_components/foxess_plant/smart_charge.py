"""Smart charge — combine Solcast forecast with tariff rates for grid charging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .models import ChargePeriodConfig
from .octopus_tariff import _parse_api_dt, rate_at
from .solcast_forecast_metrics import compute_forecast_metrics


@dataclass(frozen=True)
class RateSlot:
    start: datetime
    end: datetime
    import_p_per_kwh: float
    export_p_per_kwh: float | None = None

    @property
    def duration_hours(self) -> float:
        return max(0.0, (self.end - self.start).total_seconds() / 3600.0)


@dataclass
class SmartChargeDecision:
    action: str
    reason: str
    charge_periods: list[ChargePeriodConfig] = field(default_factory=list)
    target_max_soc: float | None = None
    deficit_kwh: float | None = None
    forecast_kwh: float | None = None
    windows: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "deficit_kwh": self.deficit_kwh,
            "forecast_kwh": self.forecast_kwh,
            "windows": self.windows,
            "charge_periods": [p.to_dict() for p in self.charge_periods],
            "target_max_soc": self.target_max_soc,
        }


def battery_deficit_kwh(
    *,
    soc_pct: float | None,
    capacity_kwh: float | None,
    kwh_remaining: float | None,
    target_soc_pct: float,
) -> float | None:
    if target_soc_pct <= 0:
        return None
    if kwh_remaining is not None and capacity_kwh is not None and capacity_kwh > 0:
        target_kwh = capacity_kwh * target_soc_pct / 100.0
        return max(0.0, target_kwh - max(0.0, kwh_remaining))
    if soc_pct is not None and capacity_kwh is not None and capacity_kwh > 0:
        return max(0.0, capacity_kwh * (target_soc_pct - soc_pct) / 100.0)
    return None


def solcast_remaining_kwh(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    metrics = compute_forecast_metrics(None, rows)
    value = metrics.get("forecast_remaining_today_kwh")
    return float(value) if value is not None else None


def rate_slots_from_octopus(
    import_rates: list[dict[str, Any]],
    export_rates: list[dict[str, Any]] | None,
    *,
    horizon_hours: int = 30,
) -> list[RateSlot]:
    now = dt_util.utcnow()
    end = now + timedelta(hours=horizon_hours)
    slots: list[RateSlot] = []
    for row in import_rates:
        start = _parse_api_dt(row.get("valid_from"))
        stop = _parse_api_dt(row.get("valid_to"))
        if start is None:
            continue
        if stop is None:
            stop = end
        if stop <= now or start >= end:
            continue
        seg_start = max(start, now)
        seg_end = min(stop, end)
        try:
            import_p = float(row.get("value_inc_vat"))
        except (TypeError, ValueError):
            continue
        export_p = rate_at(seg_start, export_rates or []) if export_rates else None
        slots.append(
            RateSlot(
                start=seg_start,
                end=seg_end,
                import_p_per_kwh=import_p,
                export_p_per_kwh=export_p,
            )
        )
    slots.sort(key=lambda s: s.start)
    return slots


def rate_slots_from_schedule(
    tariff: Any,
    *,
    horizon_hours: int = 30,
) -> list[RateSlot]:
    from .tariff_rates import scheduled_rates_at

    now = dt_util.now()
    end = now + timedelta(hours=horizon_hours)
    slots: list[RateSlot] = []
    cursor = now.replace(minute=0, second=0, microsecond=0)
    if cursor < now:
        cursor += timedelta(hours=1)
    while cursor < end:
        nxt = min(cursor + timedelta(hours=1), end)
        scheduled = scheduled_rates_at(tariff, cursor)
        slots.append(
            RateSlot(
                start=dt_util.as_utc(cursor),
                end=dt_util.as_utc(nxt),
                import_p_per_kwh=float(scheduled.get("import_p_per_kwh") or 0),
                export_p_per_kwh=float(scheduled.get("export_p_per_kwh") or 0),
            )
        )
        cursor = nxt
    return slots


def _fmt_hhmm(when: datetime) -> str:
    return dt_util.as_local(when).strftime("%H:%M")


def _slot_score(
    slot: RateSlot,
    *,
    max_export_p: float,
    round_trip_efficiency: float,
    min_arbitrage_p_per_kwh: float,
) -> float:
    import_p = slot.import_p_per_kwh
    if import_p < 0:
        export_ref = slot.export_p_per_kwh if slot.export_p_per_kwh is not None else max_export_p
        profit = (export_ref + abs(import_p)) * round_trip_efficiency
        return profit if profit >= min_arbitrage_p_per_kwh else -999.0
    return -import_p


def _merge_slots(slots: list[RateSlot]) -> list[RateSlot]:
    if not slots:
        return []
    merged: list[RateSlot] = [slots[0]]
    for slot in slots[1:]:
        prev = merged[-1]
        if slot.start <= prev.end and abs(slot.import_p_per_kwh - prev.import_p_per_kwh) < 0.001:
            merged[-1] = RateSlot(
                start=prev.start,
                end=max(prev.end, slot.end),
                import_p_per_kwh=prev.import_p_per_kwh,
                export_p_per_kwh=prev.export_p_per_kwh,
            )
        else:
            merged.append(slot)
    return merged


def _best_contiguous_block(
    slots: list[RateSlot],
    *,
    max_export_p: float,
    round_trip_efficiency: float,
    min_arbitrage_p_per_kwh: float,
) -> tuple[list[RateSlot], float] | None:
    if not slots:
        return None
    scored = [
        (
            _slot_score(
                slot,
                max_export_p=max_export_p,
                round_trip_efficiency=round_trip_efficiency,
                min_arbitrage_p_per_kwh=min_arbitrage_p_per_kwh,
            ),
            slot,
        )
        for slot in slots
    ]
    best_sum = -999999.0
    best_range: tuple[int, int] | None = None
    for i in range(len(scored)):
        run = 0.0
        for j in range(i, len(scored)):
            run += scored[j][0]
            if run > best_sum:
                best_sum = run
                best_range = (i, j)
    if best_range is None or best_sum <= -900:
        return None
    start, end = best_range
    block = [scored[k][1] for k in range(start, end + 1)]
    return block, best_sum


def _periods_from_block(
    block: list[RateSlot],
    templates: list[ChargePeriodConfig],
) -> list[ChargePeriodConfig]:
    if not block:
        return [ChargePeriodConfig.from_dict(p.to_dict()) for p in templates[:2]]
    start = block[0].start
    end = block[-1].end
    primary = ChargePeriodConfig.from_dict(templates[0].to_dict())
    primary.enable_force_charge = True
    primary.enable_charge_from_grid = True
    primary.start = _fmt_hhmm(start)
    primary.end = _fmt_hhmm(end)
    periods = [primary]
    if len(templates) > 1:
        periods.append(ChargePeriodConfig.from_dict(templates[1].to_dict()))
    while len(periods) < 2:
        periods.append(ChargePeriodConfig())
    return periods[:2]


def evaluate_smart_charge(
    *,
    config: Any,
    soc_pct: float | None,
    capacity_kwh: float | None,
    kwh_remaining: float | None,
    forecast_rows: list[dict[str, Any]],
    import_slots: list[RateSlot],
    export_slots: list[RateSlot] | None = None,
) -> SmartChargeDecision:
    """Decide whether to grid-charge based on solar forecast and tariff timeline."""
    templates = list(getattr(config, "charge_periods", []) or [])
    if len(templates) < 2:
        templates = templates + [ChargePeriodConfig()] * (2 - len(templates))

    deficit = battery_deficit_kwh(
        soc_pct=soc_pct,
        capacity_kwh=capacity_kwh,
        kwh_remaining=kwh_remaining,
        target_soc_pct=float(getattr(config, "target_soc", 100.0) or 100.0),
    )
    forecast_kwh = solcast_remaining_kwh(forecast_rows)
    target_max_soc = getattr(config, "target_max_soc", None)
    if target_max_soc is None:
        target_max_soc = getattr(config, "target_soc", None)

    if deficit is None:
        return SmartChargeDecision(
            action="idle",
            reason="Battery SOC or capacity unavailable",
            deficit_kwh=deficit,
            forecast_kwh=forecast_kwh,
        )

    min_deficit = float(getattr(config, "min_deficit_kwh", 0.5) or 0.5)
    if deficit <= min_deficit:
        return SmartChargeDecision(
            action="skip",
            reason=f"Battery near target ({deficit:.1f} kWh deficit)",
            deficit_kwh=round(deficit, 2),
            forecast_kwh=forecast_kwh,
            target_max_soc=target_max_soc,
        )

    safety = float(getattr(config, "solar_safety_margin", 1.15) or 1.15)
    if forecast_kwh is not None and forecast_kwh * safety >= deficit:
        return SmartChargeDecision(
            action="skip",
            reason=(
                f"Solar forecast {forecast_kwh:.1f} kWh covers "
                f"{deficit:.1f} kWh deficit (×{safety:.2f} margin)"
            ),
            deficit_kwh=round(deficit, 2),
            forecast_kwh=round(forecast_kwh, 2),
            target_max_soc=target_max_soc,
        )

    if not import_slots:
        return SmartChargeDecision(
            action="idle",
            reason="No import rate timeline available",
            deficit_kwh=round(deficit, 2),
            forecast_kwh=forecast_kwh,
        )

    merged = _merge_slots(import_slots)
    export_values = [
        float(s.export_p_per_kwh)
        for s in (export_slots or merged)
        if s.export_p_per_kwh is not None
    ]
    max_export_p = max(export_values) if export_values else 0.0

    block_result = _best_contiguous_block(
        merged,
        max_export_p=max_export_p,
        round_trip_efficiency=float(getattr(config, "round_trip_efficiency", 0.9) or 0.9),
        min_arbitrage_p_per_kwh=float(getattr(config, "min_arbitrage_p_per_kwh", 0.5) or 0.5),
    )
    if block_result is None:
        return SmartChargeDecision(
            action="skip",
            reason="No beneficial import window found",
            deficit_kwh=round(deficit, 2),
            forecast_kwh=forecast_kwh,
            target_max_soc=target_max_soc,
        )

    block, _score = block_result
    periods = _periods_from_block(block, templates)
    import_p = block[0].import_p_per_kwh
    if import_p < 0:
        reason = f"Negative import {import_p:.2f}p/kWh arbitrage ({deficit:.1f} kWh deficit)"
        action = "arbitrage"
    else:
        reason = (
            f"Grid charge {periods[0].start}-{periods[0].end} at "
            f"{import_p:.2f}p/kWh ({deficit:.1f} kWh deficit, forecast {forecast_kwh or 0:.1f} kWh)"
        )
        action = "grid_charge"

    windows = [
        {
            "start": _fmt_hhmm(block[0].start),
            "end": _fmt_hhmm(block[-1].end),
            "import_p_per_kwh": round(import_p, 4),
        }
    ]
    return SmartChargeDecision(
        action=action,
        reason=reason,
        charge_periods=periods,
        target_max_soc=target_max_soc,
        deficit_kwh=round(deficit, 2),
        forecast_kwh=forecast_kwh,
        windows=windows,
    )
