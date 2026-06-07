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
        start_t = _parse_hhmm(self.start)
        end_t = _parse_hhmm(self.end)
        if (
            self.enable_force_charge
            and start_t.hour == 0
            and start_t.minute == 0
            and (end_t.hour, end_t.minute) != (0, 0)
        ):
            start_t = time(hour=0, minute=1)
        return {
            "enable_force_charge": self.enable_force_charge,
            "enable_charge_from_grid": self.enable_charge_from_grid,
            "start": start_t,
            "end": end_t,
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
    storm_weather_categories: list[str] | None = None
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
        raw_categories = data.get("storm_weather_categories")
        if raw_categories is not None:
            storm_weather_categories = list(raw_categories)
        elif raw_types is not None:
            from .storm_weather import categories_from_google_types

            storm_weather_categories = categories_from_google_types(list(raw_types) if raw_types else [])
        else:
            storm_weather_categories = None
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
            storm_weather_categories=storm_weather_categories,
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
        if self.storm_weather_categories is not None:
            out["storm_weather_categories"] = self.storm_weather_categories
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
class PvStringConfig:
    """Physical PV string settings for analysis and forecasting."""

    enabled: bool = True
    panel_count: int = 6
    watts_per_panel: int = 450
    efficiency_factor: float = 100.0
    tilt: int = 25
    azimuth: int = 180

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, defaults: dict[str, Any] | None = None) -> PvStringConfig:
        base = defaults or {}
        raw_count = data.get("panel_count", base.get("panel_count", 6))
        raw_watts = data.get("watts_per_panel", base.get("watts_per_panel", 450))
        raw_eff = data.get("efficiency_factor", base.get("efficiency_factor", 100.0))
        try:
            panel_count = int(raw_count)
        except (TypeError, ValueError):
            panel_count = 6
        try:
            watts_per_panel = int(raw_watts)
        except (TypeError, ValueError):
            watts_per_panel = 450
        try:
            efficiency_factor = float(raw_eff)
        except (TypeError, ValueError):
            efficiency_factor = 100.0
        panel_count = max(1, min(12, panel_count))
        watts_per_panel = max(100, min(1000, watts_per_panel))
        efficiency_factor = max(1.0, min(100.0, efficiency_factor))
        try:
            tilt = int(data.get("tilt", base.get("tilt", 25)))
        except (TypeError, ValueError):
            tilt = 25
        try:
            azimuth = int(data.get("azimuth", base.get("azimuth", 180)))
        except (TypeError, ValueError):
            azimuth = 180
        tilt = max(0, min(90, tilt))
        azimuth = max(0, min(359, azimuth))
        return cls(
            enabled=bool(data.get("enabled", base.get("enabled", True))),
            panel_count=panel_count,
            watts_per_panel=watts_per_panel,
            efficiency_factor=efficiency_factor,
            tilt=tilt,
            azimuth=azimuth,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "panel_count": self.panel_count,
            "watts_per_panel": self.watts_per_panel,
            "efficiency_factor": self.efficiency_factor,
            "tilt": self.tilt,
            "azimuth": self.azimuth,
        }

    @property
    def nameplate_dc_w(self) -> float:
        return float(self.panel_count * self.watts_per_panel)

    @property
    def effective_dc_w(self) -> float:
        return self.nameplate_dc_w * (self.efficiency_factor / 100.0)


@dataclass
class SolcastConfig:
    """Solcast hobbyist API settings (stored in config entry)."""

    enabled: bool = False
    api_key: str | None = None
    api_limit: int = 10
    auto_update: str = "daylight"
    latitude: float | None = None
    longitude: float | None = None
    installation_date: str | None = None
    period: str = "PT30M"
    fetch_pv_forecast: bool = True
    api_used_today: int = 0
    api_used_date: str | None = None
    last_fetch_at: str | None = None
    last_error: str | None = None
    rooftop_site_bindings: dict[str, str] = field(default_factory=dict)
    rooftop_sites_meta: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SolcastConfig:
        from .const import DEFAULT_SOLCAST, DEFAULT_SOLCAST_API_LIMIT, SOLCAST_AUTO_UPDATE_DAYLIGHT

        base = DEFAULT_SOLCAST
        raw_limit = data.get("api_limit", base.get("api_limit", DEFAULT_SOLCAST_API_LIMIT))
        try:
            api_limit = int(raw_limit)
        except (TypeError, ValueError):
            api_limit = DEFAULT_SOLCAST_API_LIMIT
        api_limit = max(1, min(50, api_limit))
        auto = str(data.get("auto_update", base.get("auto_update", SOLCAST_AUTO_UPDATE_DAYLIGHT)))
        if auto not in ("daylight", "all_day"):
            auto = SOLCAST_AUTO_UPDATE_DAYLIGHT
        from .solcast_weather import parse_solcast_coordinates, parse_solcast_installation_date

        coords = parse_solcast_coordinates(data.get("latitude"), data.get("longitude"))
        lat, lon = coords if coords else (None, None)
        install_date = parse_solcast_installation_date(
            data.get("installation_date", base.get("installation_date"))
        )
        raw_bindings = data.get("rooftop_site_bindings", base.get("rooftop_site_bindings", {}))
        bindings = (
            {str(k): str(v) for k, v in raw_bindings.items() if v}
            if isinstance(raw_bindings, dict)
            else {}
        )
        raw_meta = data.get("rooftop_sites_meta", base.get("rooftop_sites_meta", []))
        sites_meta = [m for m in raw_meta if isinstance(m, dict)] if isinstance(raw_meta, list) else []
        return cls(
            enabled=bool(data.get("enabled", base.get("enabled", False))),
            api_key=str(data["api_key"]) if data.get("api_key") else None,
            api_limit=api_limit,
            auto_update=auto,
            latitude=lat,
            longitude=lon,
            installation_date=install_date,
            period=str(data.get("period", base.get("period", "PT30M"))),
            fetch_pv_forecast=bool(data.get("fetch_pv_forecast", base.get("fetch_pv_forecast", True))),
            api_used_today=int(data.get("api_used_today", 0) or 0),
            api_used_date=data.get("api_used_date"),
            last_fetch_at=data.get("last_fetch_at"),
            last_error=data.get("last_error"),
            rooftop_site_bindings=bindings,
            rooftop_sites_meta=sites_meta,
        )

    def to_dict(self, *, include_api_key: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "enabled": self.enabled,
            "api_limit": self.api_limit,
            "auto_update": self.auto_update,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "installation_date": self.installation_date,
            "period": self.period,
            "fetch_pv_forecast": self.fetch_pv_forecast,
            "api_used_today": self.api_used_today,
            "api_used_date": self.api_used_date,
            "last_fetch_at": self.last_fetch_at,
            "last_error": self.last_error,
            "rooftop_site_bindings": dict(self.rooftop_site_bindings),
            "rooftop_sites_meta": list(self.rooftop_sites_meta),
        }
        if include_api_key:
            out["api_key"] = self.api_key
        else:
            out["api_key_set"] = bool(self.api_key)
        out["coordinates_configured"] = self.coordinates_configured()
        out["hobbyist_sites_resolved"] = self.hobbyist_sites_resolved()
        return out

    def hobbyist_sites_resolved(self) -> bool:
        return bool(self.rooftop_site_bindings)

    def api_key_configured(self) -> bool:
        return bool(self.api_key and str(self.api_key).strip())

    def coordinates_configured(self) -> bool:
        from .solcast_weather import parse_solcast_coordinates

        return parse_solcast_coordinates(self.latitude, self.longitude) is not None


@dataclass
class TariffDynamicConfig:
    """Octopus API or external entity-backed dynamic tariffs (e.g. Agile)."""

    enabled: bool = False
    provider: str = ""
    source: str = "native"
    api_key: str | None = None
    account_number: str | None = None
    import_mpan: str | None = None
    export_mpan: str | None = None
    import_entity: str | None = None
    export_entity: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> TariffDynamicConfig:
        raw = data if isinstance(data, dict) else {}
        import_entity = raw.get("import_entity")
        export_entity = raw.get("export_entity")
        import_mpan = raw.get("import_mpan")
        export_mpan = raw.get("export_mpan")
        account_number = raw.get("account_number")
        source = str(raw.get("source") or "native").strip().lower()
        if source not in ("native", "entity"):
            source = "native"
        return cls(
            enabled=bool(raw.get("enabled", False)),
            provider=str(raw.get("provider") or "").strip(),
            source=source,
            api_key=str(raw["api_key"]) if raw.get("api_key") else None,
            account_number=str(account_number).strip().upper() if account_number else None,
            import_mpan=str(import_mpan).strip() if import_mpan else None,
            export_mpan=str(export_mpan).strip() if export_mpan else None,
            import_entity=str(import_entity) if import_entity else None,
            export_entity=str(export_entity) if export_entity else None,
        )

    def api_key_configured(self) -> bool:
        return bool(self.api_key and str(self.api_key).strip())

    def native_octopus(self) -> bool:
        from .octopus_tariff import OCTOPUS_PROVIDER, OCTOPUS_SOURCE_NATIVE

        return (
            self.enabled
            and self.provider == OCTOPUS_PROVIDER
            and self.source == OCTOPUS_SOURCE_NATIVE
        )

    def to_dict(self, *, include_api_key: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "enabled": self.enabled,
            "provider": self.provider,
            "source": self.source,
            "account_number": self.account_number,
            "import_mpan": self.import_mpan,
            "export_mpan": self.export_mpan,
            "import_entity": self.import_entity,
            "export_entity": self.export_entity,
        }
        if include_api_key:
            out["api_key"] = self.api_key
        else:
            out["api_key_set"] = self.api_key_configured()
        return out


@dataclass
class TariffConfig:
    """Electricity tariff for cost analysis (schedule, plugin sensors, or external entities)."""

    kind: str = "static"
    currency: str = "GBP"
    import_source: str = "schedule"
    import_entity: str | None = None
    import_p_per_kwh: float = 0.0
    export_source: str = "schedule"
    export_entity: str | None = None
    export_p_per_kwh: float = 0.0
    standing_source: str = "plugin"
    standing_entity: str | None = None
    standing_charge_p_per_day: float = 0.0
    schedule: Any = None  # TariffScheduleConfig — lazy import to avoid circular refs
    dynamic: TariffDynamicConfig = field(default_factory=TariffDynamicConfig)
    last_updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> TariffConfig:
        from .const import DEFAULT_TARIFF, TARIFF_KIND_STATIC
        from .tariff_currency import normalize_tariff_currency
        from .tariff_rates import (
            TARIFF_SOURCE_ENTITY,
            TARIFF_SOURCE_MANUAL,
            TARIFF_SOURCE_PLUGIN,
            TARIFF_SOURCE_SCHEDULE,
        )
        from .tariff_schedule import (
            TariffScheduleConfig,
            migrate_legacy_manual_to_schedule,
        )

        raw = {**DEFAULT_TARIFF, **(data if isinstance(data, dict) else {})}
        kind = str(raw.get("kind") or TARIFF_KIND_STATIC)
        if kind not in ("static", "dynamic"):
            kind = TARIFF_KIND_STATIC

        def _rate(key: str) -> float:
            try:
                return max(0.0, float(raw.get(key, 0) or 0))
            except (TypeError, ValueError):
                return 0.0

        def _import_source() -> str:
            value = str(raw.get("import_source") or TARIFF_SOURCE_SCHEDULE)
            if value == TARIFF_SOURCE_MANUAL:
                return TARIFF_SOURCE_SCHEDULE
            return value if value in (TARIFF_SOURCE_SCHEDULE, TARIFF_SOURCE_ENTITY) else TARIFF_SOURCE_SCHEDULE

        def _export_source() -> str:
            value = str(raw.get("export_source") or TARIFF_SOURCE_SCHEDULE)
            if value == TARIFF_SOURCE_MANUAL:
                return TARIFF_SOURCE_SCHEDULE
            return value if value in (TARIFF_SOURCE_SCHEDULE, TARIFF_SOURCE_ENTITY) else TARIFF_SOURCE_SCHEDULE

        def _standing_source() -> str:
            value = str(raw.get("standing_source") or TARIFF_SOURCE_PLUGIN)
            if value == TARIFF_SOURCE_MANUAL:
                return TARIFF_SOURCE_PLUGIN
            return (
                value
                if value in (TARIFF_SOURCE_PLUGIN, TARIFF_SOURCE_ENTITY)
                else TARIFF_SOURCE_PLUGIN
            )

        def _entity(key: str) -> str | None:
            value = raw.get(key)
            return str(value) if value else None

        import_p = _rate("import_p_per_kwh")
        export_p = _rate("export_p_per_kwh")
        schedule = migrate_legacy_manual_to_schedule(
            TariffScheduleConfig.from_dict(raw.get("schedule")),
            import_p=import_p,
            export_p=export_p,
        )

        return cls(
            kind=kind,
            currency=normalize_tariff_currency(raw.get("currency")),
            import_source=_import_source(),
            import_entity=_entity("import_entity"),
            import_p_per_kwh=import_p,
            export_source=_export_source(),
            export_entity=_entity("export_entity"),
            export_p_per_kwh=export_p,
            standing_source=_standing_source(),
            standing_entity=_entity("standing_entity"),
            standing_charge_p_per_day=_rate("standing_charge_p_per_day"),
            schedule=schedule,
            dynamic=TariffDynamicConfig.from_dict(raw.get("dynamic")),
            last_updated_at=raw.get("last_updated_at"),
        )

    def schedule_config(self):
        from .tariff_schedule import TariffScheduleConfig

        if isinstance(self.schedule, TariffScheduleConfig):
            return self.schedule
        return TariffScheduleConfig.from_dict(self.schedule if isinstance(self.schedule, dict) else {})

    def to_dict(self, *, include_secrets: bool = False) -> dict[str, Any]:
        schedule = self.schedule_config()
        return {
            "kind": self.kind,
            "currency": self.currency,
            "import_source": self.import_source,
            "import_entity": self.import_entity,
            "import_p_per_kwh": round(self.import_p_per_kwh, 4),
            "export_source": self.export_source,
            "export_entity": self.export_entity,
            "export_p_per_kwh": round(self.export_p_per_kwh, 4),
            "standing_source": self.standing_source,
            "standing_entity": self.standing_entity,
            "standing_charge_p_per_day": round(self.standing_charge_p_per_day, 4),
            "schedule": schedule.to_dict(),
            "dynamic": self.dynamic.to_dict(include_api_key=include_secrets),
            "last_updated_at": self.last_updated_at,
        }

    def _rate_configured(self, source: str, manual_p: float, entity_id: str | None) -> bool:
        from .tariff_rates import TARIFF_SOURCE_ENTITY, TARIFF_SOURCE_PLUGIN, TARIFF_SOURCE_SCHEDULE

        if source == TARIFF_SOURCE_ENTITY:
            return bool(entity_id)
        if source == TARIFF_SOURCE_PLUGIN:
            return manual_p > 0
        if source == TARIFF_SOURCE_SCHEDULE:
            schedule = self.schedule_config()
            if manual_p > 0:
                return True
            return any(
                band.import_p_per_kwh > 0 or band.export_p_per_kwh > 0 for band in schedule.bands
            )
        return False

    def configured(self) -> bool:
        from .tariff_rates import TARIFF_SOURCE_SCHEDULE

        schedule = self.schedule_config()
        import_ok = self._rate_configured(
            self.import_source, self.import_p_per_kwh, self.import_entity
        )
        export_ok = self._rate_configured(
            self.export_source, self.export_p_per_kwh, self.export_entity
        )
        standing_ok = self._rate_configured(
            self.standing_source, self.standing_charge_p_per_day, self.standing_entity
        )
        if not import_ok and self.import_source == TARIFF_SOURCE_SCHEDULE:
            import_ok = any(b.import_p_per_kwh > 0 for b in schedule.bands)
        if not export_ok and self.export_source == TARIFF_SOURCE_SCHEDULE:
            export_ok = any(b.export_p_per_kwh > 0 for b in schedule.bands)
        return import_ok or export_ok or standing_ok or self.dynamic.enabled

    def rates_snapshot(self, *, effective: dict[str, float] | None = None) -> dict[str, float | str | None]:
        """Normalized rates for history store / future recorder sensors."""
        eff = effective or {}
        return {
            "kind": self.kind,
            "currency": self.currency,
            "import_p_per_kwh": round(
                float(eff.get("import_p_per_kwh", self.import_p_per_kwh)), 4
            ),
            "export_p_per_kwh": round(
                float(eff.get("export_p_per_kwh", self.export_p_per_kwh)), 4
            ),
            "standing_charge_p_per_day": round(
                float(eff.get("standing_charge_p_per_day", self.standing_charge_p_per_day)), 4
            ),
            "import_source": self.import_source,
            "export_source": self.export_source,
            "standing_source": self.standing_source,
            "import_entity": self.import_entity,
            "export_entity": self.export_entity,
            "standing_entity": self.standing_entity,
        }


@dataclass
class PvSystemConfig:
    """PV1 / PV2 configuration for the plant."""

    pv1: PvStringConfig = field(default_factory=PvStringConfig)
    pv2: PvStringConfig = field(
        default_factory=lambda: PvStringConfig(enabled=False, panel_count=1)
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PvSystemConfig:
        from .const import DEFAULT_PV_CONFIG

        pv1_defaults = DEFAULT_PV_CONFIG["pv1"]
        pv2_defaults = DEFAULT_PV_CONFIG["pv2"]
        return cls(
            pv1=PvStringConfig.from_dict(data.get("pv1", {}), defaults=pv1_defaults),
            pv2=PvStringConfig.from_dict(data.get("pv2", {}), defaults=pv2_defaults),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pv1": self.pv1.to_dict(),
            "pv2": self.pv2.to_dict(),
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
    storm_prep: PrepPolicyConfig = field(default_factory=PrepPolicyConfig)
    outage_prep: PrepPolicyConfig = field(default_factory=PrepPolicyConfig)
    forecast_prep: ForecastPrepConfig = field(default_factory=ForecastPrepConfig)
    panel_display: PanelDisplayConfig = field(default_factory=PanelDisplayConfig)
    pv_config: PvSystemConfig = field(default_factory=PvSystemConfig)
    solcast: SolcastConfig = field(default_factory=SolcastConfig)
    tariff: TariffConfig = field(default_factory=TariffConfig)
    tariff_modes: dict[str, list[ChargePeriodConfig]] = field(default_factory=dict)

    @classmethod
    def from_entry_data(cls, data: dict[str, Any]) -> PlantConfig:
        from .const import (
            DEFAULT_BASELINE_PERIODS,
            DEFAULT_FORECAST_PREP,
            DEFAULT_OUTAGE_PREP,
            DEFAULT_PANEL_DISPLAY,
            DEFAULT_PV_CONFIG,
            DEFAULT_SOLCAST,
            DEFAULT_STORM_PREP,
            DEFAULT_TARIFF,
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
            pv_config=PvSystemConfig.from_dict(data.get("pv_config", DEFAULT_PV_CONFIG)),
            solcast=SolcastConfig.from_dict(data.get("solcast", DEFAULT_SOLCAST)),
            tariff=TariffConfig.from_dict(data.get("tariff", DEFAULT_TARIFF)),
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
            "pv_config": self.pv_config.to_dict(),
            "solcast": self.solcast.to_dict(),
            "tariff": self.tariff.to_dict(include_secrets=True),
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
