"""Data models for foxess_plant."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import time
from typing import Any


def _parse_hhmm(value: str) -> time:
    parts = value.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return time(hour=hour, minute=minute)


def _format_hhmm(value: time) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


@dataclass
class ChargePeriodConfig:
    """Single charge period definition."""

    enable_force_charge: bool = False
    enable_charge_from_grid: bool = False
    start: str = "00:00"
    end: str = "00:00"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChargePeriodConfig:
        return cls(
            enable_force_charge=bool(data.get("enable_force_charge", False)),
            enable_charge_from_grid=bool(data.get("enable_charge_from_grid", False)),
            start=str(data.get("start", "00:00")),
            end=str(data.get("end", "00:00")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_service_dict(self) -> dict[str, Any]:
        return {
            "enable_force_charge": self.enable_force_charge,
            "enable_charge_from_grid": self.enable_charge_from_grid,
            "start": _parse_hhmm(self.start),
            "end": _parse_hhmm(self.end),
        }

    def matches_modbus_state(
        self,
        force_charge_on: bool,
        grid_on: bool,
        start_state: str | None,
        end_state: str | None,
    ) -> bool:
        if self.enable_force_charge != force_charge_on:
            return False
        if self.enable_charge_from_grid != grid_on:
            return False
        if not self.enable_force_charge:
            return True
        expected_start = f"{_parse_hhmm(self.start).hour:02d}:{_parse_hhmm(self.start).minute:02d}:00"
        expected_end = f"{_parse_hhmm(self.end).hour:02d}:{_parse_hhmm(self.end).minute:02d}:00"
        return start_state == expected_start and end_state == expected_end


@dataclass
class ControlConfig:
    exclusive: bool = True
    drift_check_interval: int = 300
    on_drift: str = "reapply"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ControlConfig:
        return cls(
            exclusive=bool(data.get("exclusive", True)),
            drift_check_interval=int(data.get("drift_check_interval", 300)),
            on_drift=str(data.get("on_drift", "reapply")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OverrideState:
    active: bool = False
    mode: str = "baseline"
    periods: list[ChargePeriodConfig] | None = None
    reason: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OverrideState:
        periods_raw = data.get("periods")
        periods = (
            [ChargePeriodConfig.from_dict(p) for p in periods_raw]
            if isinstance(periods_raw, list)
            else None
        )
        return cls(
            active=bool(data.get("active", False)),
            mode=str(data.get("mode", "baseline")),
            periods=periods,
            reason=str(data.get("reason", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "mode": self.mode,
            "periods": [p.to_dict() for p in self.periods] if self.periods else None,
            "reason": self.reason,
        }


@dataclass
class PlantConfig:
    device_id: str
    inverter_target: str
    entity_map: dict[str, str] = field(default_factory=dict)
    baseline_periods: list[ChargePeriodConfig] = field(default_factory=list)
    control: ControlConfig = field(default_factory=ControlConfig)
    override: OverrideState = field(default_factory=OverrideState)
    control_active: bool = True

    @classmethod
    def from_entry_data(cls, data: dict[str, Any]) -> PlantConfig:
        baseline = [
            ChargePeriodConfig.from_dict(p)
            for p in data.get("baseline_periods", [])
        ]
        return cls(
            device_id=data["device_id"],
            inverter_target=data["inverter_target"],
            entity_map=dict(data.get("entity_map", {})),
            baseline_periods=baseline,
            control=ControlConfig.from_dict(data.get("control", {})),
            override=OverrideState.from_dict(data.get("override", {})),
            control_active=bool(data.get("control_active", True)),
        )

    def to_entry_data(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "inverter_target": self.inverter_target,
            "entity_map": self.entity_map,
            "baseline_periods": [p.to_dict() for p in self.baseline_periods],
            "control": self.control.to_dict(),
            "override": self.override.to_dict(),
            "control_active": self.control_active,
        }

    def desired_periods(self) -> list[ChargePeriodConfig]:
        if self.override.active and self.override.periods:
            return self.override.periods
        return self.baseline_periods

    def plant_mode(self) -> str:
        if not self.control_active:
            return "manual"
        if self.override.active:
            return self.override.mode
        return "baseline"
