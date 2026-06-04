"""Plant coordinator — central control for charge periods and drift detection."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .analytics import compute_analytics
from .impact import compute_impact
from .charge_period import apply_charge_periods
from .discovery import missing_charge_period_entities
from .flow_scene import resolve_flow_scene_theme
from .soc_limits import apply_soc_limits, clamp_soc_values
from .const import (
    ANALYTICS_ENTITY_SUFFIXES,
    IMPACT_ENTITY_SUFFIXES,
    AUTOMATION_MODES,
    CONF_PANEL_DISPLAY,
    CONF_PV_CONFIG,
    CONF_SOLCAST,
    CONF_STORM_PREP,
    IDENTITY_ENTITY_SUFFIXES,
    EVENT_BASELINE_RESTORED,
    EVENT_CONTROL_DRIFT,
    EVENT_EXTERNAL_WRITE,
    EVENT_FORECAST_ARMED,
    EVENT_FORECAST_DISARMED,
    EVENT_OUTAGE_ARMED,
    EVENT_OUTAGE_DISARMED,
    EVENT_PERIOD_APPLIED,
    EVENT_PERIOD_APPLY_FAILED,
    EVENT_STORM_ARMED,
    EVENT_STORM_DISARMED,
    EVENT_TARIFF_APPLIED,
    MODE_FORECAST,
    MODE_OUTAGE,
    MODE_STORM,
    MODE_TARIFF,
    TRIGGER_ON_STATES,
)
from .models import (
    ChargePeriodConfig,
    OverrideState,
    PanelDisplayConfig,
    PlantConfig,
    PvSystemConfig,
    SolcastConfig,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


class FoxessPlantCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinates plant policy, Modbus writes, and drift detection."""

    config_entry: ConfigEntry
    plant: PlantConfig
    _unsub_drift: callable | None = None
    _unsub_triggers: callable | None = None
    _applying: bool = False
    _active_storm_triggers: set[str]
    _active_outage_triggers: set[str]
    _forecast_armed: bool
    _storm_forecast_active: bool
    _storm_forecast_detail: dict[str, Any]

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.plant = PlantConfig.from_entry_data(entry.data)
        self._active_storm_triggers = set()
        self._active_outage_triggers = set()
        self._forecast_armed = False
        self._storm_forecast_active = False
        self._storm_forecast_detail = {}
        self._solcast_cache: dict[str, Any] = {}
        self._solcast_store = None
        self._solcast_history_count = 0
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"FoxESS Plant {entry.title}",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_load_solcast_storage(self) -> None:
        """Restore forecast cache from HA .storage (parsed + raw API documents)."""
        from .solcast_store import SolcastForecastStore, cache_from_storage

        self._solcast_store = SolcastForecastStore(self.hass, self.config_entry.entry_id)
        stored = await self._solcast_store.async_load()
        self._solcast_cache = cache_from_storage(stored)
        self._solcast_history_count = SolcastForecastStore.history_count(stored)
        if self._solcast_detailed_forecast_rows():
            _LOGGER.debug(
                "Restored Solcast forecast from storage (%s history snapshots)",
                self._solcast_history_count,
            )
            await self._maybe_repair_solcast_storage(stored)

    def _solcast_detailed_forecast_rows(self) -> list[dict[str, Any]]:
        parsed = self._solcast_cache.get("pv_forecast_parsed")
        if not isinstance(parsed, dict):
            return []
        rows = parsed.get("detailed_forecast")
        return rows if isinstance(rows, list) else []

    async def _maybe_repair_solcast_storage(self, stored: dict[str, Any]) -> None:
        """Rewrite .storage current when forecast was recovered from history only."""
        if not self._solcast_store or not self._solcast_cache.get("pv_forecast_parsed"):
            return
        current = stored.get("current")
        if isinstance(current, dict) and current.get("pv_forecast_parsed"):
            return
        self._solcast_history_count = await self._solcast_store.async_record_poll(
            self._solcast_cache
        )
        _LOGGER.info("Repaired Solcast forecast storage from history snapshot")

    async def async_ensure_solcast_cache(self) -> None:
        """Load persisted forecast if memory is empty or missing detailed rows (e.g. early panel open)."""
        if len(self._solcast_detailed_forecast_rows()) >= 2:
            return
        await self._async_load_solcast_storage()

    async def async_config_entry_first_refresh(self) -> None:
        await self._async_load_solcast_storage()
        self._sync_trigger_membership()
        self.setup_trigger_listeners()
        await super().async_config_entry_first_refresh()
        self._setup_drift_timer()
        self._setup_storm_forecast_timer()
        self._setup_solcast_timer()
        try:
            await self._async_refresh_storm_weather()
            await self._async_refresh_solcast_pv()
            await self._sync_automation_policy()
        except Exception as err:
            _LOGGER.warning("Initial automation policy sync failed: %s", err)
        if self.plant.control_active:
            try:
                await self.async_apply_desired(force=True)
            except Exception as err:
                _LOGGER.warning("Initial baseline apply failed: %s", err)

    def _setup_drift_timer(self) -> None:
        if self._unsub_drift:
            self._unsub_drift()
            self._unsub_drift = None
        interval = max(60, self.plant.control.drift_check_interval)
        self._unsub_drift = async_track_time_interval(
            self.hass,
            self._drift_timer_callback,
            timedelta(seconds=interval),
        )

    @callback
    def _drift_timer_callback(self, _now) -> None:
        self.hass.async_create_task(self.async_check_drift())

    def _setup_storm_forecast_timer(self) -> None:
        if getattr(self, "_unsub_storm_forecast", None):
            self._unsub_storm_forecast()
            self._unsub_storm_forecast = None
        self._unsub_storm_forecast = async_track_time_interval(
            self.hass,
            self._storm_forecast_timer_callback,
            timedelta(minutes=15),
        )

    @callback
    def _storm_forecast_timer_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_refresh_storm_weather())

    def _setup_solcast_timer(self) -> None:
        if getattr(self, "_unsub_solcast", None):
            self._unsub_solcast()
            self._unsub_solcast = None
        self._unsub_solcast = async_track_time_interval(
            self.hass,
            self._solcast_timer_callback,
            timedelta(minutes=5),
        )

    @callback
    def _solcast_timer_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_refresh_solcast_pv())

    def _solcast_pv_active(self) -> bool:
        sc = self.plant.solcast
        return bool(
            sc.enabled
            and sc.api_key_configured()
            and sc.fetch_pv_forecast
            and sc.coordinates_configured()
        )

    async def _async_refresh_solcast_pv(self, *, force: bool = False) -> None:
        """Poll Solcast rooftop PV forecast (Google Weather handles storms/overview)."""
        if not self._solcast_pv_active():
            return
        from .solcast_poll import async_refresh_solcast

        cache_before_updated = self._solcast_cache.get("updated_at")
        self._solcast_cache = await async_refresh_solcast(
            self.hass, self.plant, self._solcast_cache, force=force
        )
        if (
            self._solcast_store
            and self._solcast_cache.get("pv_forecast_parsed")
            and self._solcast_cache.get("updated_at") != cache_before_updated
        ):
            self._solcast_history_count = await self._solcast_store.async_record_poll(
                self._solcast_cache
            )
            _LOGGER.debug(
                "Persisted Solcast forecast to storage (%s periods)",
                (self._solcast_cache.get("pv_forecast_parsed") or {}).get("period_count"),
            )
        self._persist_solcast_usage()
        await self.async_request_refresh()

    async def _async_refresh_storm_weather(self) -> None:
        """Re-evaluate StormSafe using Google Weather (hourly forecast + condition sensors)."""
        from .storm_forecast import async_storm_in_forecast_window

        cfg = self.plant.storm_prep
        if cfg.enabled and cfg.use_forecast_lead and cfg.weather_entity_id:
            active, detail = await async_storm_in_forecast_window(
                self.hass,
                cfg.weather_entity_id,
                cfg.forecast_lead_hours,
            )
            self._storm_forecast_active = active
            self._storm_forecast_detail = detail
        else:
            self._storm_forecast_active = False
            self._storm_forecast_detail = {}
        self._sync_trigger_membership()
        await self._sync_automation_policy()

    def _persist_solcast_usage(self) -> None:
        data = dict(self.config_entry.data)
        data[CONF_SOLCAST] = self.plant.solcast.to_dict()
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)

    def update_plant_config(self, plant: PlantConfig) -> None:
        self.plant = plant
        self._sync_trigger_membership()
        self.setup_trigger_listeners()
        self._setup_drift_timer()

    def setup_trigger_listeners(self) -> None:
        if self._unsub_triggers:
            self._unsub_triggers()
            self._unsub_triggers = None
        entities = self.plant.all_trigger_entities()
        if not entities:
            return

        @callback
        def _listener(event: Event) -> None:
            self.hass.async_create_task(self._async_handle_trigger_event(event))

        self._unsub_triggers = async_track_state_change_event(self.hass, entities, _listener)

    def _sync_trigger_membership(self) -> None:
        self._active_storm_triggers = {
            eid
            for eid in self.plant.storm_prep.trigger_entities
            if self._is_binary_trigger_active(eid)
        }
        self._sync_storm_condition_trigger()
        self._active_outage_triggers = {
            eid
            for eid in self.plant.outage_prep.trigger_entities
            if self._is_binary_trigger_active(eid)
        }

    def _sync_storm_condition_trigger(self) -> None:
        cfg = self.plant.storm_prep
        watch = {cfg.condition_entity_id, cfg.weather_entity_id} - {None}
        for eid in list(self._active_storm_triggers):
            if eid in watch:
                self._active_storm_triggers.discard(eid)
        if self._is_storm_condition_active():
            entity_id = cfg.condition_entity_id or cfg.weather_entity_id
            if entity_id:
                self._active_storm_triggers.add(entity_id)
        if self._storm_forecast_active and cfg.weather_entity_id:
            self._active_storm_triggers.add(cfg.weather_entity_id)

    def _is_binary_trigger_active(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        return state.state.lower() in TRIGGER_ON_STATES

    def _is_storm_condition_active(self) -> bool:
        from .storm_weather import is_storm_weather_active

        cfg = self.plant.storm_prep
        return is_storm_weather_active(
            self.hass,
            condition_entity_id=cfg.condition_entity_id,
            weather_entity_id=cfg.weather_entity_id,
            use_weather_condition=cfg.use_weather_condition,
            storm_types=cfg.storm_google_types,
        )

    async def _async_handle_trigger_event(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        if not entity_id or not self.plant.control_active:
            return

        storm_watch = set(self.plant.storm_prep.storm_watch_entities())
        if entity_id in storm_watch:
            self._sync_trigger_membership()
            if entity_id == self.plant.storm_prep.weather_entity_id:
                await self._async_refresh_storm_weather()
                return

        if entity_id in self.plant.outage_prep.trigger_entities:
            if self._is_binary_trigger_active(entity_id):
                self._active_outage_triggers.add(entity_id)
            else:
                self._active_outage_triggers.discard(entity_id)

        await self._sync_automation_policy()

    async def _sync_automation_policy(self) -> None:
        if not self.plant.control_active:
            return
        if self.plant.override.active and self.plant.override.mode not in AUTOMATION_MODES:
            return

        if self.plant.outage_prep.enabled and self._active_outage_triggers:
            reason = f"outage:{','.join(sorted(self._active_outage_triggers))}"
            if self.plant.override.active and self.plant.override.mode == MODE_OUTAGE:
                if self.plant.override.reason == reason:
                    return
            await self._arm_policy(
                MODE_OUTAGE,
                self.plant.outage_prep.charge_periods,
                reason,
                self.plant.outage_prep.target_max_soc,
                EVENT_OUTAGE_ARMED,
            )
            return

        if self.plant.storm_prep.enabled and self._active_storm_triggers:
            reason = f"storm:{','.join(sorted(self._active_storm_triggers))}"
            if self.plant.override.active and self.plant.override.mode == MODE_STORM:
                if self.plant.override.reason == reason:
                    return
            await self._arm_policy(
                MODE_STORM,
                self.plant.storm_prep.charge_periods,
                reason,
                self.plant.storm_prep.target_max_soc,
                EVENT_STORM_ARMED,
            )
            return

        if self._forecast_armed:
            return

        if self.plant.override.active and self.plant.override.mode in AUTOMATION_MODES:
            mode = self.plant.override.mode
            event = {
                MODE_STORM: EVENT_STORM_DISARMED,
                MODE_OUTAGE: EVENT_OUTAGE_DISARMED,
                MODE_FORECAST: EVENT_FORECAST_DISARMED,
            }[mode]
            await self._disarm_policy(mode, event)

    async def _arm_policy(
        self,
        mode: str,
        periods: list[ChargePeriodConfig],
        reason: str,
        target_max_soc: float | None,
        event_name: str,
    ) -> None:
        await self._save_max_soc_if_needed(target_max_soc)
        await self.async_set_override_periods(periods, mode, reason)
        if target_max_soc is not None:
            await self._set_max_soc(target_max_soc)
        self._fire(event_name, {"reason": reason, "mode": mode})

    async def _disarm_policy(self, mode: str, event_name: str) -> None:
        if not (self.plant.override.active and self.plant.override.mode == mode):
            return
        saved = self.plant.override.saved_max_soc
        self.plant.override = OverrideState()
        await self._persist()
        await self.async_apply_desired()
        if saved is not None:
            await self._set_max_soc(saved)
        self._fire(event_name, {})
        self._fire(EVENT_BASELINE_RESTORED, {})

    async def _evaluate_forecast_prep(self) -> None:
        cfg = self.plant.forecast_prep
        if not cfg.enabled or not cfg.forecast_entity or not self.plant.control_active:
            return
        if self.plant.outage_prep.enabled and self._active_outage_triggers:
            return
        if self.plant.storm_prep.enabled and self._active_storm_triggers:
            return

        state = self.hass.states.get(cfg.forecast_entity)
        if state is None or state.state in ("unknown", "unavailable"):
            return

        try:
            forecast_kwh = float(state.state)
        except (TypeError, ValueError):
            return

        low_forecast = forecast_kwh < cfg.threshold_kwh
        if low_forecast and not self._forecast_armed:
            self._forecast_armed = True
            if self.plant.override.active and self.plant.override.mode not in AUTOMATION_MODES:
                return
            await self._arm_policy(
                MODE_FORECAST,
                cfg.charge_periods,
                f"forecast:{forecast_kwh:.1f}<{cfg.threshold_kwh}",
                cfg.target_max_soc,
                EVENT_FORECAST_ARMED,
            )
        elif not low_forecast and self._forecast_armed:
            self._forecast_armed = False
            if self.plant.override.active and self.plant.override.mode == MODE_FORECAST:
                await self._disarm_policy(MODE_FORECAST, EVENT_FORECAST_DISARMED)

    async def _save_max_soc_if_needed(self, target: float | None) -> None:
        if target is None or self.plant.override.saved_max_soc is not None:
            return
        current = self._entity_state("max_soc")
        if current not in (None, "unknown", "unavailable"):
            try:
                self.plant.override.saved_max_soc = float(current)
            except ValueError:
                pass

    async def _set_max_soc(self, value: float) -> None:
        current = {
            "min_soc": self._entity_float("min_soc"),
            "min_soc_on_grid": self._entity_float("min_soc_on_grid"),
            "max_soc": self._entity_float("max_soc"),
        }
        target = clamp_soc_values(
            int(current.get("min_soc") or 10),
            int(current.get("min_soc_on_grid") or 10),
            int(round(value)),
        )
        await apply_soc_limits(
            self.hass,
            self.plant.entity_map,
            min_soc=target["min_soc"],
            min_soc_on_grid=target["min_soc_on_grid"],
            max_soc=target["max_soc"],
            current=current,
        )

    async def async_set_soc_limits(
        self,
        min_soc: int,
        min_soc_on_grid: int,
        max_soc: int,
    ) -> None:
        """Write all three SOC limits in an inverter-safe order."""
        await apply_soc_limits(
            self.hass,
            self.plant.entity_map,
            min_soc=min_soc,
            min_soc_on_grid=min_soc_on_grid,
            max_soc=max_soc,
            force_write=True,
            verify=True,
        )

    async def _persist(self) -> None:
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=self.plant.to_entry_data(),
        )

    def _storm_prep_state(self) -> dict[str, Any]:
        from .storm_weather import read_condition_snapshot

        out = self.plant.storm_prep.to_dict()
        out["weather_provider"] = "google_weather"
        out["current_condition"] = read_condition_snapshot(
            self.hass,
            self.plant.storm_prep.condition_entity_id,
            self.plant.storm_prep.weather_entity_id,
            storm_types=self.plant.storm_prep.storm_google_types,
        )
        out["condition_active"] = self._is_storm_condition_active()
        out["forecast_active"] = self._storm_forecast_active
        out["forecast_detail"] = self._storm_forecast_detail
        return out

    def _overview_weather_state(self) -> dict[str, Any] | None:
        from .storm_weather import read_overview_weather

        return read_overview_weather(self.hass, self.plant.storm_prep)

    def _solcast_state(self) -> dict[str, Any]:
        from .solcast_poll import solcast_status_dict

        return solcast_status_dict(
            self.plant.solcast,
            self._solcast_cache,
            plant=self.plant,
            hass=self.hass,
            forecast_history_snapshots=self._solcast_history_count,
        )

    def get_plant_state(self) -> dict[str, Any]:
        from .panel import get_panel_disk_info

        desired = [p.to_dict() for p in self.plant.desired_periods()]
        actual = self._read_actual_periods()
        drift = self._compute_drift(desired, actual)
        analytics = self._read_analytics()
        impact = self._read_impact()
        return {
            "plant_id": self.config_entry.entry_id,
            "title": self.config_entry.title,
            "flow_scene_theme": resolve_flow_scene_theme(self.hass),
            "inverter": self.plant.inverter_target,
            "inverter_device_id": self.plant.device_id,
            "charge_periods_ready": not missing_charge_period_entities(self.plant.entity_map),
            "control_active": self.plant.control_active,
            "mode": self.plant.plant_mode(),
            "override_active": self.plant.override.active,
            "override_reason": self.plant.override.reason,
            "desired_periods": desired,
            "baseline_periods": [p.to_dict() for p in self.plant.baseline_periods],
            "actual_periods": actual,
            "drift": drift,
            "entity_map": self.plant.entity_map,
            "analytics": analytics,
            "impact": impact,
            "active_storm_triggers": sorted(self._active_storm_triggers),
            "active_outage_triggers": sorted(self._active_outage_triggers),
            "forecast_armed": self._forecast_armed,
            "tariff_modes": sorted(self.plant.tariff_modes.keys()),
            "storm_prep": self._storm_prep_state(),
            "overview_weather": self._overview_weather_state(),
            "outage_prep": self.plant.outage_prep.to_dict(),
            "panel_display": self.plant.panel_display.to_dict(),
            "pv_config": self.plant.pv_config.to_dict(),
            "solcast": self._solcast_state(),
            "panel_runtime": get_panel_disk_info(),
            "settings": {
                "max_soc": self._entity_float("max_soc"),
                "min_soc": self._entity_float("min_soc"),
                "min_soc_on_grid": self._entity_float("min_soc_on_grid"),
                "work_mode": self._entity_state("work_mode"),
                "work_mode_options": self._entity_options("work_mode"),
            },
            "identity": self._read_identity(),
        }

    def _read_analytics(self) -> dict[str, Any]:
        states = {key: self._entity_state(key) for key in ANALYTICS_ENTITY_SUFFIXES}
        if not any(states.values()):
            return {}
        return compute_analytics(states)

    def _read_impact(self) -> dict[str, Any]:
        states = {key: self._entity_state(key) for key in IMPACT_ENTITY_SUFFIXES}
        if not any(v not in (None, "unknown", "unavailable", "") for v in states.values()):
            return {}
        return compute_impact(states)

    def _read_identity(self) -> dict[str, str | None]:
        """PCS/BMS identity and firmware from discovered foxess_modbus entities."""
        return {
            key: self._entity_state(key)
            for key in IDENTITY_ENTITY_SUFFIXES
            if self.plant.entity_map.get(key)
        }

    async def _async_update_data(self) -> dict[str, Any]:
        await self.async_ensure_solcast_cache()
        try:
            await self._evaluate_forecast_prep()
        except Exception as err:
            _LOGGER.warning("Forecast prep evaluation failed: %s", err)
        return self.get_plant_state()

    def _entity_state(self, key: str) -> str | None:
        entity_id = self.plant.entity_map.get(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        return state.state if state else None

    def _entity_float(self, key: str) -> float | None:
        raw = self._entity_state(key)
        if raw in (None, "unavailable", "unknown"):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def _entity_options(self, key: str) -> list[str]:
        entity_id = self.plant.entity_map.get(key)
        if not entity_id:
            return []
        state = self.hass.states.get(entity_id)
        if not state:
            return []
        options = state.attributes.get("options")
        return list(options) if isinstance(options, list) else []

    def _read_period_from_entities(self, index: int) -> dict[str, Any]:
        prefix = f"time_period_{index}"
        force = self._entity_state(f"{prefix}_enable_force_charge")
        grid = self._entity_state(f"{prefix}_enable_charge_from_grid")
        start = self._entity_state(f"{prefix}_start")
        end = self._entity_state(f"{prefix}_end")
        return {
            "enable_force_charge": force in ("on", "true", "1"),
            "enable_charge_from_grid": grid in ("on", "true", "1"),
            "start": start,
            "end": end,
        }

    def _read_actual_periods(self) -> list[dict[str, Any]]:
        count = max(2, len(self.plant.baseline_periods))
        return [self._read_period_from_entities(i + 1) for i in range(count)]

    def _compute_drift(
        self,
        desired: list[dict[str, Any]],
        actual: list[dict[str, Any]],
    ) -> bool:
        for i, want in enumerate(desired):
            if i >= len(actual):
                return True
            got = actual[i]
            if bool(want.get("enable_force_charge")) != bool(got.get("enable_force_charge")):
                return True
            if bool(want.get("enable_charge_from_grid")) != bool(got.get("enable_charge_from_grid")):
                return True
            if want.get("enable_force_charge"):
                want_start = want.get("start", "00:00")
                want_end = want.get("end", "00:00")
                if len(want_start) == 5:
                    want_start = f"{want_start}:00"
                if len(want_end) == 5:
                    want_end = f"{want_end}:00"
                if got.get("start") != want_start or got.get("end") != want_end:
                    return True
        return False

    def _fire(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        payload = {"plant_id": self.config_entry.entry_id, **(data or {})}
        self.hass.bus.async_fire(event_type, payload)

    async def async_apply_desired(self, force: bool = False) -> None:
        if not self.plant.control_active and not force:
            raise HomeAssistantError("Plant control is released; enable control before applying")

        periods = self.plant.desired_periods()
        if not periods:
            raise HomeAssistantError("No charge periods configured")

        self._applying = True
        try:
            await apply_charge_periods(
                self.hass,
                self.plant.inverter_target,
                periods,
                entity_map=self.plant.entity_map,
            )
            self._fire(
                EVENT_PERIOD_APPLIED,
                {
                    "mode": self.plant.plant_mode(),
                    "periods": [p.to_dict() for p in periods],
                },
            )
        except Exception as err:
            self._fire(EVENT_PERIOD_APPLY_FAILED, {"error": str(err)})
            raise HomeAssistantError(f"Failed to apply charge periods: {err}") from err
        finally:
            self._applying = False
            await self.async_request_refresh()

    async def async_apply_baseline(self) -> None:
        saved = self.plant.override.saved_max_soc
        self.plant.override = OverrideState()
        self._forecast_armed = False
        await self._persist()
        await self.async_apply_desired()
        if saved is not None:
            await self._set_max_soc(saved)
        self._fire(EVENT_BASELINE_RESTORED, {})

    async def async_set_baseline_periods(self, periods: list[ChargePeriodConfig]) -> None:
        self.plant.baseline_periods = periods
        if not self.plant.override.active:
            await self.async_apply_desired()
        await self._persist()

    async def async_set_charge_period(
        self,
        period_index: int,
        period: ChargePeriodConfig,
        apply_now: bool = True,
    ) -> None:
        if period_index < 1 or period_index > 2:
            raise HomeAssistantError("charge_period must be 1 or 2")
        idx = period_index - 1
        while len(self.plant.baseline_periods) <= idx:
            self.plant.baseline_periods.append(ChargePeriodConfig())
        self.plant.baseline_periods[idx] = period
        if apply_now and not self.plant.override.active:
            await self.async_apply_desired()
        await self._persist()

    async def async_set_override_periods(
        self,
        periods: list[ChargePeriodConfig],
        mode: str,
        reason: str,
    ) -> None:
        self.plant.override.active = True
        self.plant.override.mode = mode
        self.plant.override.periods = periods
        self.plant.override.reason = reason
        await self._persist()
        await self.async_apply_desired()

    async def async_disarm_override(self) -> None:
        mode = self.plant.override.mode
        saved = self.plant.override.saved_max_soc
        self.plant.override = OverrideState()
        self._forecast_armed = False
        self._active_storm_triggers.clear()
        self._active_outage_triggers.clear()
        await self._persist()
        await self.async_apply_desired()
        if saved is not None:
            await self._set_max_soc(saved)
        if mode == MODE_STORM:
            self._fire(EVENT_STORM_DISARMED, {})
        elif mode == MODE_OUTAGE:
            self._fire(EVENT_OUTAGE_DISARMED, {})
        elif mode == MODE_FORECAST:
            self._fire(EVENT_FORECAST_DISARMED, {})
        self._fire(EVENT_BASELINE_RESTORED, {})

    async def async_arm_storm_prep(
        self,
        periods: list[ChargePeriodConfig] | None,
        reason: str = "storm_prep",
    ) -> None:
        use_periods = periods if periods else self.plant.storm_prep.charge_periods
        await self._arm_policy(MODE_STORM, use_periods, reason, self.plant.storm_prep.target_max_soc, EVENT_STORM_ARMED)

    async def async_save_storm_prep(
        self,
        *,
        enabled: bool,
        trigger_entities: list[str],
        charge_periods: list[dict[str, Any]],
        target_max_soc: float | None,
        alert_provider: str | None = None,
        google_weather_entry_id: str | None = None,
        use_forecast_lead: bool | None = None,
        forecast_lead_hours: int | None = None,
    ) -> None:
        """Persist storm prep from the Fox Plant panel."""
        from .panel_config import resolve_google_weather_entry

        periods = [ChargePeriodConfig.from_dict(p) for p in charge_periods]
        triggers = list(trigger_entities)
        use_weather_condition = True
        use_forecast = True if use_forecast_lead is None else use_forecast_lead
        lead_hours = 4 if forecast_lead_hours is None else max(1, min(int(forecast_lead_hours), 48))
        condition_entity_id: str | None = None
        weather_entity_id: str | None = None
        if google_weather_entry_id:
            sources = resolve_google_weather_entry(self.hass, google_weather_entry_id)
            if sources["alert_trigger_ids"]:
                triggers = sources["alert_trigger_ids"]
            condition_entity_id = sources["condition_entity_id"]
            weather_entity_id = sources["weather_entity_id"]
            use_weather_condition = bool(condition_entity_id)
            if use_forecast_lead is None:
                use_forecast = bool(weather_entity_id)
        data = dict(self.config_entry.data)
        storm_data: dict[str, Any] = {
            "enabled": enabled,
            "use_weather_condition": use_weather_condition,
            "use_forecast_lead": use_forecast,
            "forecast_lead_hours": lead_hours,
            "trigger_entities": triggers,
            "charge_periods": [p.to_dict() for p in periods],
            "target_max_soc": target_max_soc,
        }
        if alert_provider:
            storm_data["alert_provider"] = alert_provider
        if google_weather_entry_id:
            storm_data["google_weather_entry_id"] = google_weather_entry_id
        if condition_entity_id:
            storm_data["condition_entity_id"] = condition_entity_id
        if weather_entity_id:
            storm_data["weather_entity_id"] = weather_entity_id
        data[CONF_STORM_PREP] = storm_data
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        await self._async_refresh_storm_weather()
        await self.async_request_refresh()

    async def async_save_panel_display(self, *, forecast_entity_id: str | None) -> None:
        """Persist Fox Plant chart options from the panel."""
        entity_id = forecast_entity_id.strip() if forecast_entity_id else None
        if entity_id:
            st = self.hass.states.get(entity_id)
            if st is None:
                raise HomeAssistantError(f"Entity {entity_id} is not available")
            if not entity_id.startswith("sensor."):
                raise HomeAssistantError(f"{entity_id} must be a sensor entity")
        data = dict(self.config_entry.data)
        data[CONF_PANEL_DISPLAY] = PanelDisplayConfig(forecast_entity_id=entity_id).to_dict()
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        await self.async_request_refresh()

    async def async_save_pv_config(self, *, pv_config: dict[str, Any]) -> None:
        """Persist PV1/PV2 physical configuration from the panel."""
        data = dict(self.config_entry.data)
        data[CONF_PV_CONFIG] = PvSystemConfig.from_dict(pv_config).to_dict()
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        if self._solcast_pv_active():
            await self._async_refresh_solcast_pv(force=True)
        await self.async_request_refresh()

    async def async_save_solcast(self, *, solcast: dict[str, Any], fetch_now: bool = True) -> None:
        """Persist Solcast API settings from the panel."""
        from .solcast_weather import parse_solcast_coordinates, parse_solcast_installation_date

        fetch_now = bool(solcast.pop("fetch_now", fetch_now))
        current = self.plant.solcast.to_dict()
        merged = {**current, **solcast}
        if "installation_date" in solcast:
            raw_install = solcast.get("installation_date")
            if raw_install is None or str(raw_install).strip() == "":
                merged["installation_date"] = None
            else:
                install_date = parse_solcast_installation_date(raw_install)
                if install_date is None:
                    raise HomeAssistantError(
                        "Installation date must be YYYY-MM-DD (match your Solcast site listing)."
                    )
                merged["installation_date"] = install_date
        if merged.get("enabled"):
            coords = parse_solcast_coordinates(merged.get("latitude"), merged.get("longitude"))
            if coords is None:
                raise HomeAssistantError(
                    "Solcast latitude and longitude are required when enabled. "
                    "Copy the values exactly from one of your two registered locations "
                    "on the Solcast website (not Home Assistant home coordinates)."
                )
            merged["latitude"], merged["longitude"] = coords
        if "api_key" in solcast:
            raw_key = solcast.get("api_key")
            if raw_key and str(raw_key).strip() and str(raw_key) not in ("********", "••••••••"):
                merged["api_key"] = str(raw_key).strip()
            else:
                merged["api_key"] = current.get("api_key")
        data = dict(self.config_entry.data)
        data[CONF_SOLCAST] = SolcastConfig.from_dict(merged).to_dict()
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        if merged.get("enabled") and self.plant.solcast.api_key_configured():
            from .solcast_hobbyist import async_resolve_rooftop_bindings

            try:
                await async_resolve_rooftop_bindings(self.hass, self.plant)
            except SolcastApiError as err:
                raise HomeAssistantError(str(err)) from err
            data = dict(self.config_entry.data)
            data[CONF_SOLCAST] = self.plant.solcast.to_dict()
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            self.update_plant_config(PlantConfig.from_entry_data(data))
        if fetch_now and self._solcast_pv_active():
            await self._async_refresh_solcast_pv(force=True)
        await self.async_request_refresh()

    async def async_test_solcast(self) -> dict[str, Any]:
        """Verify Solcast hobbyist API key by listing Home PV sites (no quota use)."""
        from .solcast_api import SolcastApiError
        from .solcast_poll import async_test_solcast_connection, solcast_status_dict

        if not self.plant.solcast.api_key_configured():
            raise HomeAssistantError("Solcast API key is not configured")
        test_result = await async_test_solcast_connection(
            self.hass, self.plant.solcast, plant=self.plant
        )
        status = solcast_status_dict(
            self.plant.solcast,
            self._solcast_cache,
            plant=self.plant,
            hass=self.hass,
            forecast_history_snapshots=self._solcast_history_count,
        )
        status.update(test_result)
        if not test_result.get("test_ok"):
            raise HomeAssistantError(test_result.get("error") or "Solcast test failed")
        return status

    async def async_set_tariff_mode(self, mode_name: str) -> None:
        if mode_name not in self.plant.tariff_modes:
            raise HomeAssistantError(f"Unknown tariff mode '{mode_name}'")
        periods = self.plant.tariff_modes[mode_name]
        await self.async_set_override_periods(periods, MODE_TARIFF, f"tariff:{mode_name}")
        self._fire(EVENT_TARIFF_APPLIED, {"reason": f"tariff:{mode_name}", "mode": MODE_TARIFF})

    async def async_set_tariff_profile(
        self,
        mode_name: str,
        periods: list[ChargePeriodConfig],
    ) -> None:
        self.plant.tariff_modes[mode_name] = periods
        await self._persist()

    async def async_take_control(self) -> None:
        self.plant.control_active = True
        await self._persist()
        await self.async_apply_desired(force=True)

    async def async_release_control(self) -> None:
        self.plant.control_active = False
        await self._persist()
        await self.async_request_refresh()

    async def async_check_drift(self) -> None:
        if not self.plant.control.exclusive or not self.plant.control_active:
            return
        if self._applying:
            return

        state = self.get_plant_state()
        if not state["drift"]:
            return

        self._fire(
            EVENT_CONTROL_DRIFT,
            {"desired": state["desired_periods"], "actual": state["actual_periods"]},
        )
        self._fire(
            EVENT_EXTERNAL_WRITE,
            {"desired": state["desired_periods"], "actual": state["actual_periods"]},
        )

        if self.plant.control.on_drift == "reapply":
            _LOGGER.warning("Charge period drift detected; reapplying desired state")
            try:
                await self.async_apply_desired()
            except HomeAssistantError as err:
                _LOGGER.error("Drift reapply failed: %s", err)
        elif self.plant.control.on_drift == "alert":
            _LOGGER.warning("Charge period drift detected (alert only)")

    async def async_shutdown(self) -> None:
        if self._unsub_drift:
            self._unsub_drift()
            self._unsub_drift = None
        if getattr(self, "_unsub_storm_forecast", None):
            self._unsub_storm_forecast()
            self._unsub_storm_forecast = None
        if getattr(self, "_unsub_solcast", None):
            self._unsub_solcast()
            self._unsub_solcast = None
        if self._unsub_triggers:
            self._unsub_triggers()
            self._unsub_triggers = None
