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
    saved_max_soc: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OverrideState:
        periods_raw = data.get("periods")
        periods = (
            [ChargePeriodConfig.from_dict(p) for p in periods_raw]
            if isinstance(periods_raw, list)
            else None
        )
        saved = data.get("saved_max_soc")
        return cls(
            active=bool(data.get("active", False)),
            mode=str(data.get("mode", "baseline")),
            periods=periods,
            reason=str(data.get("reason", "")),
            saved_max_soc=float(saved) if saved is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "mode": self.mode,
            "periods": [p.to_dict() for p in self.periods] if self.periods else None,
            "reason": self.reason,
            "saved_max_soc": self.saved_max_soc,
        }


@dataclass
class PrepPolicyConfig:
    enabled: bool = False
    alert_provider: str | None = None
    google_weather_entry_id: str | None = None
    use_weather_condition: bool = True
    use_forecast_lead: bool = True
    forecast_lead_hours: int = 4
    condition_entity_id: str | None = None
    weather_entity_id: str | None = None
    storm_google_types: list[str] | None = None
    trigger_entities: list[str] = field(default_factory=list)
    charge_periods: list[ChargePeriodConfig] = field(default_factory=list)
    target_max_soc: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], default_periods: list[dict[str, Any]]) -> PrepPolicyConfig:
        periods_raw = data.get("charge_periods") or default_periods
        target = data.get("target_max_soc")
        provider = data.get("alert_provider")
        gw_entry = data.get("google_weather_entry_id")
        condition_entity = data.get("condition_entity_id")
        weather_entity = data.get("weather_entity_id")
        raw_types = data.get("storm_google_types")
        return cls(
            enabled=bool(data.get("enabled", False)),
            alert_provider=str(provider) if provider else None,
            google_weather_entry_id=str(gw_entry) if gw_entry else None,
            use_weather_condition=bool(data.get("use_weather_condition", True)),
            use_forecast_lead=bool(data.get("use_forecast_lead", True)),
            forecast_lead_hours=int(data.get("forecast_lead_hours", 4)),
            condition_entity_id=str(condition_entity) if condition_entity else None,
            weather_entity_id=str(weather_entity) if weather_entity else None,
            storm_google_types=list(raw_types) if raw_types else None,
            trigger_entities=list(data.get("trigger_entities", [])),
            charge_periods=[ChargePeriodConfig.from_dict(p) for p in periods_raw],
            target_max_soc=float(target) if target is not None else None,
        )

    def storm_watch_entities(self) -> list[str]:
        entities = list(self.trigger_entities)
        if self.use_weather_condition:
            if self.condition_entity_id:
                entities.append(self.condition_entity_id)
            if self.weather_entity_id:
                entities.append(self.weather_entity_id)
        return sorted(set(entities))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "enabled": self.enabled,
            "use_weather_condition": self.use_weather_condition,
            "use_forecast_lead": self.use_forecast_lead,
            "forecast_lead_hours": self.forecast_lead_hours,
            "trigger_entities": self.trigger_entities,
            "charge_periods": [p.to_dict() for p in self.charge_periods],
            "target_max_soc": self.target_max_soc,
        }
        if self.alert_provider:
            out["alert_provider"] = self.alert_provider
        if self.google_weather_entry_id:
            out["google_weather_entry_id"] = self.google_weather_entry_id
        if self.condition_entity_id:
            out["condition_entity_id"] = self.condition_entity_id
        if self.weather_entity_id:
            out["weather_entity_id"] = self.weather_entity_id
        if self.storm_google_types:
            out["storm_google_types"] = self.storm_google_types
        return out


@dataclass
class ForecastPrepConfig:
    enabled: bool = False
    forecast_entity: str | None = None
    threshold_kwh: float = 5.0
    charge_periods: list[ChargePeriodConfig] = field(default_factory=list)
    target_max_soc: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], default_periods: list[dict[str, Any]]) -> ForecastPrepConfig:
        periods_raw = data.get("charge_periods") or default_periods
        target = data.get("target_max_soc")
        return cls(
            enabled=bool(data.get("enabled", False)),
            forecast_entity=data.get("forecast_entity"),
            threshold_kwh=float(data.get("threshold_kwh", 5.0)),
            charge_periods=[ChargePeriodConfig.from_dict(p) for p in periods_raw],
            target_max_soc=float(target) if target is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "forecast_entity": self.forecast_entity,
            "threshold_kwh": self.threshold_kwh,
            "charge_periods": [p.to_dict() for p in self.charge_periods],
            "target_max_soc": self.target_max_soc,
        }


@dataclass
class PanelDisplayConfig:
    """Fox Plant panel display options (charts, etc.)."""

    forecast_entity_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PanelDisplayConfig:
        raw = data.get("forecast_entity_id")
        return cls(forecast_entity_id=str(raw) if raw else None)

    def to_dict(self) -> dict[str, Any]:
        return {"forecast_entity_id": self.forecast_entity_id}


@dataclass
class PlantConfig:
    device_id: str
    inverter_target: str
    entity_map: dict[str, str] = field(default_factory=dict)
    baseline_periods: list[ChargePeriodConfig] = field(default_factory=list)
    control: ControlConfig = field(default_factory=ControlConfig)
    override: OverrideState = field(default_factory=OverrideState)
    control_active: bool = True
    storm_prep: PrepPolicyConfig = field(default_factory=PrepPolicyConfig)
    outage_prep: PrepPolicyConfig = field(default_factory=PrepPolicyConfig)
    forecast_prep: ForecastPrepConfig = field(default_factory=ForecastPrepConfig)
    panel_display: PanelDisplayConfig = field(default_factory=PanelDisplayConfig)
    tariff_modes: dict[str, list[ChargePeriodConfig]] = field(default_factory=dict)

    @classmethod
    def from_entry_data(cls, data: dict[str, Any]) -> PlantConfig:
        from .const import (
            DEFAULT_BASELINE_PERIODS,
            DEFAULT_FORECAST_PREP,
            DEFAULT_OUTAGE_PREP,
            DEFAULT_PANEL_DISPLAY,
            DEFAULT_STORM_PREP,
        )

        baseline = [ChargePeriodConfig.from_dict(p) for p in data.get("baseline_periods", DEFAULT_BASELINE_PERIODS)]
        tariff_raw = data.get("tariff_modes", {})
        tariff_modes = {
            name: [ChargePeriodConfig.from_dict(p) for p in periods]
            for name, periods in tariff_raw.items()
            if isinstance(periods, list)
        }
        return cls(
            device_id=data["device_id"],
            inverter_target=data.get("inverter_target", data["device_id"]),
            entity_map=dict(data.get("entity_map", {})),
            baseline_periods=baseline,
            control=ControlConfig.from_dict(data.get("control", {})),
            override=OverrideState.from_dict(data.get("override", {})),
            control_active=bool(data.get("control_active", True)),
            storm_prep=PrepPolicyConfig.from_dict(data.get("storm_prep", {}), DEFAULT_STORM_PREP["charge_periods"]),
            outage_prep=PrepPolicyConfig.from_dict(data.get("outage_prep", {}), DEFAULT_OUTAGE_PREP["charge_periods"]),
            forecast_prep=ForecastPrepConfig.from_dict(
                data.get("forecast_prep", {}), DEFAULT_FORECAST_PREP["charge_periods"]
            ),
            panel_display=PanelDisplayConfig.from_dict(data.get("panel_display", DEFAULT_PANEL_DISPLAY)),
            tariff_modes=tariff_modes,
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
            "storm_prep": self.storm_prep.to_dict(),
            "outage_prep": self.outage_prep.to_dict(),
            "forecast_prep": self.forecast_prep.to_dict(),
            "panel_display": self.panel_display.to_dict(),
            "tariff_modes": {
                name: [p.to_dict() for p in periods] for name, periods in self.tariff_modes.items()
            },
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

    def all_trigger_entities(self) -> list[str]:
        entities: list[str] = []
        if self.storm_prep.enabled:
            entities.extend(self.storm_prep.storm_watch_entities())
        if self.outage_prep.enabled:
            entities.extend(self.outage_prep.trigger_entities)
        return sorted(set(entities))
