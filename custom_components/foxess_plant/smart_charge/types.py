"""Shared SmartCharge types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..models import ChargePeriodConfig


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
    operating_mode: str | None = None
    reserve_kwh: float | None = None
    exportable_kwh: float | None = None
    target_soc_effective: float | None = None
    grid_gap_kwh: float | None = None
    dark_hours_kwh: float | None = None
    daily_plan: list[dict[str, Any]] = field(default_factory=list)
    eval_tier: str | None = None
    discharge_window: dict[str, Any] | None = None
    work_mode_target: str | None = None
    planned_export_kwh: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "deficit_kwh": self.deficit_kwh,
            "forecast_kwh": self.forecast_kwh,
            "windows": self.windows,
            "charge_periods": [p.to_dict() for p in self.charge_periods],
            "target_max_soc": self.target_max_soc,
            "operating_mode": self.operating_mode,
            "reserve_kwh": self.reserve_kwh,
            "exportable_kwh": self.exportable_kwh,
            "target_soc_effective": self.target_soc_effective,
            "grid_gap_kwh": self.grid_gap_kwh,
            "dark_hours_kwh": self.dark_hours_kwh,
            "daily_plan": self.daily_plan,
            "eval_tier": self.eval_tier,
            "discharge_window": self.discharge_window,
            "work_mode_target": self.work_mode_target,
            "planned_export_kwh": self.planned_export_kwh,
        }


def discharge_window_signature(window: dict[str, Any] | None) -> str:
    if not window:
        return ""
    return (
        f"{window.get('start')}|{window.get('end')}|"
        f"{window.get('export_p_per_kwh')}"
    )


def charge_periods_signature(periods: list[ChargePeriodConfig]) -> str:
    parts: list[str] = []
    for period in periods[:2]:
        parts.append(
            f"{period.start}|{period.end}|{period.enable_force_charge}|{period.enable_charge_from_grid}"
        )
    return ";".join(parts)
