"""Plant coordinator — central control for charge periods and drift detection."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .analytics import compute_analytics
from .impact import compute_impact
from .charge_period import apply_charge_periods
from .discovery import missing_charge_period_entities
from .remote_control import is_charge_period_modbus_blocked
from .remote_control import periods_want_grid_force_charge
from .remote_control import set_remote_control_mode
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
    CONF_TARIFF,
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
    TariffConfig,
    TariffDynamicConfig,
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
        self._solcast_forecast_chart_points: list[dict[str, float]] = []
        self._tariff_store = None
        self._tariff_history_count = 0
        self._tariff_rate_sensors: dict[str, Any] = {}
        self._unsub_tariff_schedule: callable | None = None
        self._unsub_octopus: callable | None = None
        self._last_tariff_sensor_rates: dict[str, float] = {}
        self._octopus_cache: dict[str, Any] = {}
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

        try:
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
            await self._rebuild_solcast_forecast_chart()
            self.hass.async_create_task(self._safe_archive_solcast_daily_forecasts())
        except Exception:
            _LOGGER.exception("Solcast storage load failed; continuing without persisted forecast")
            self._solcast_store = None
            self._solcast_cache = {}
            self._solcast_history_count = 0
            self._solcast_forecast_chart_points = []

    async def _safe_archive_solcast_daily_forecasts(self) -> None:
        """Archive daily charts without blocking or breaking coordinator startup."""
        try:
            await self._archive_solcast_daily_forecasts()
        except Exception:
            _LOGGER.exception("Solcast daily forecast archive failed")

    async def _archive_solcast_daily_forecasts(self) -> None:
        """Persist per-day forecast chart lines so Analysis can show past days."""
        if not self._solcast_store:
            return
        from .solcast_forecast_chart import archive_daily_intraday_forecasts

        stored = await self._solcast_store.async_load()
        updates = await self.hass.async_add_executor_job(
            archive_daily_intraday_forecasts,
            self.hass,
            stored,
            self._solcast_cache,
            entry_id=self.config_entry.entry_id,
            use_recorder=False,
        )
        if updates:
            await self._solcast_store.async_merge_daily_intraday(updates)
            _LOGGER.debug(
                "Archived Solcast daily forecast charts for %s",
                ", ".join(sorted(updates.keys())),
            )

    async def _async_load_tariff_storage(self) -> None:
        from .tariff_store import TariffRateStore

        self._tariff_store = TariffRateStore(self.hass, self.config_entry.entry_id)
        stored = await self._tariff_store.async_load()
        self._tariff_history_count = TariffRateStore.history_count(stored)

    def _tariff_state(self) -> dict[str, Any]:
        from .tariff_rates import resolve_tariff_rates
        from .tariff_schedule import tariff_plugin_entity_id

        state = self.plant.tariff.to_dict()
        resolved = resolve_tariff_rates(
            self.hass, self.plant.tariff, entry_id=self.config_entry.entry_id
        )
        state["configured"] = self.plant.tariff.configured()
        state["rate_history_count"] = self._tariff_history_count
        state["effective"] = resolved["effective"]
        state["entities"] = resolved["entities"]
        state["schedule_status"] = resolved.get("schedule") or {}
        entry_id = self.config_entry.entry_id
        state["plugin_sensors"] = {
            kind: tariff_plugin_entity_id(self.hass, entry_id, kind)
            for kind in ("import", "export", "standing")
        }
        state["octopus"] = self._octopus_status()
        return state

    def _octopus_native_active(self) -> bool:
        return self.plant.tariff.dynamic.native_octopus() and self.plant.tariff.dynamic.api_key_configured()

    def _octopus_agile_active(self) -> bool:
        from .octopus_tariff import is_variable_tariff_type

        if not self._octopus_native_active():
            return False
        tariff_type = self._octopus_cache.get("tariff_type")
        return bool(tariff_type and is_variable_tariff_type(str(tariff_type)))

    def _octopus_status(self) -> dict[str, Any]:
        dyn = self.plant.tariff.dynamic.to_dict(include_api_key=False)
        cache = self._octopus_cache
        import_meters = cache.get("import_meters") or []
        export_meters = cache.get("export_meters") or []
        return {
            **dyn,
            "connected": bool(cache.get("import_tariff_code")),
            "tariff_type": cache.get("tariff_type"),
            "import_tariff_code": cache.get("import_tariff_code"),
            "export_tariff_code": cache.get("export_tariff_code"),
            "import_product_code": cache.get("import_product_code"),
            "export_product_code": cache.get("export_product_code"),
            "last_fetch_at": cache.get("last_fetch_at"),
            "last_error": cache.get("last_error"),
            "current_import_p_per_kwh": cache.get("current_import_p_per_kwh"),
            "current_export_p_per_kwh": cache.get("current_export_p_per_kwh"),
            "schedule_ready": bool(cache.get("schedule")),
            "import_meters": import_meters,
            "export_meters": export_meters,
            "import_meter": cache.get("import_meter"),
            "export_meter": cache.get("export_meter"),
        }

    def register_tariff_rate_sensor(self, kind: str, sensor: Any) -> None:
        """Called from sensor platform setup."""
        self._tariff_rate_sensors[kind] = sensor

    async def async_update_tariff_sensors(self, *, record_history: bool = True) -> None:
        """Push current tariff rates to plugin sensors (schedule boundaries / save)."""
        from .tariff_rates import (
            TARIFF_SOURCE_ENTITY,
            TARIFF_SOURCE_PLUGIN,
            TARIFF_SOURCE_SCHEDULE,
            resolve_tariff_rates,
        )
        from .tariff_schedule import scheduled_rates_at

        tariff = self.plant.tariff
        scheduled = scheduled_rates_at(tariff)
        band_index = scheduled.get("band_index")
        agile = self._octopus_agile_active()

        updates: dict[str, tuple[float | None, int | None]] = {}
        if agile:
            updates["import"] = (
                self._octopus_cache.get("current_import_p_per_kwh"),
                None,
            )
            export_p = self._octopus_cache.get("current_export_p_per_kwh")
            updates["export"] = (export_p, None) if export_p is not None else (None, None)
        elif tariff.import_source == TARIFF_SOURCE_SCHEDULE:
            updates["import"] = (float(scheduled.get("import_p_per_kwh") or 0), band_index)
        else:
            updates["import"] = (None, None)

        if not agile:
            if tariff.export_source == TARIFF_SOURCE_SCHEDULE:
                updates["export"] = (float(scheduled.get("export_p_per_kwh") or 0), band_index)
            else:
                updates["export"] = (None, None)

        if tariff.standing_source == TARIFF_SOURCE_PLUGIN:
            updates["standing"] = (
                max(0.0, float(tariff.standing_charge_p_per_day or 0)),
                None,
            )
        else:
            updates["standing"] = (None, None)

        changed = False
        for kind, (minor, band) in updates.items():
            sensor = self._tariff_rate_sensors.get(kind)
            if sensor is None:
                continue
            prev = self._last_tariff_sensor_rates.get(kind)
            if minor is None:
                sensor.set_rate(None, band_index=band)
            else:
                sensor.set_rate(float(minor), band_index=band)
                if prev != minor:
                    changed = True
                    self._last_tariff_sensor_rates[kind] = float(minor)
            await sensor.async_publish()

        if record_history and changed and self._tariff_store is not None:
            resolved = resolve_tariff_rates(
                self.hass, tariff, entry_id=self.config_entry.entry_id
            )
            effective = resolved["effective"]
            source_kind = "schedule"
            if any(
                getattr(tariff, f"{key}_source") == TARIFF_SOURCE_ENTITY
                for key in ("import", "export", "standing")
            ):
                source_kind = "mixed"
            from homeassistant.util import dt as dt_util

            self._tariff_history_count = await self._tariff_store.async_record_rates(
                rates=tariff.rates_snapshot(effective=effective),
                source=source_kind,
                recorded_at=dt_util.utcnow().isoformat(),
            )

    def _setup_tariff_schedule_timer(self) -> None:
        if self._unsub_tariff_schedule:
            self._unsub_tariff_schedule()
            self._unsub_tariff_schedule = None
        if self._octopus_agile_active():
            return
        from .tariff_schedule import next_schedule_boundary

        when = next_schedule_boundary()
        self._unsub_tariff_schedule = async_track_point_in_time(
            self.hass, self._tariff_schedule_callback, when
        )

    def _setup_octopus_timer(self) -> None:
        if self._unsub_octopus:
            self._unsub_octopus()
            self._unsub_octopus = None
        if not self._octopus_native_active():
            return
        from .octopus_tariff import next_octopus_poll_boundary

        when = next_octopus_poll_boundary(agile=self._octopus_agile_active())
        self._unsub_octopus = async_track_point_in_time(self.hass, self._octopus_timer_callback, when)

    @callback
    def _octopus_timer_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_octopus_tick())

    async def _async_octopus_tick(self) -> None:
        await self._async_refresh_octopus()
        self._setup_octopus_timer()
        if self._octopus_agile_active():
            await self.async_update_tariff_sensors(record_history=True)
        await self.async_request_refresh()

    @callback
    def _tariff_schedule_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_tariff_schedule_tick())

    async def _async_tariff_schedule_tick(self) -> None:
        await self.async_update_tariff_sensors(record_history=True)
        self._setup_tariff_schedule_timer()
        await self.async_request_refresh()

    async def _rebuild_solcast_forecast_chart(self) -> None:
        from .solcast_forecast_chart import build_forecast_intraday_chart

        if not self._solcast_store:
            self._solcast_forecast_chart_points = []
            return
        stored = await self._solcast_store.async_load()
        self._solcast_forecast_chart_points = build_forecast_intraday_chart(
            self.hass, stored, self._solcast_cache
        )

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
        await self._async_load_tariff_storage()
        self._sync_trigger_membership()
        self.setup_trigger_listeners()
        await super().async_config_entry_first_refresh()
        self._setup_drift_timer()
        self._setup_storm_forecast_timer()
        self._setup_solcast_timer()
        self._setup_tariff_schedule_timer()
        self._setup_octopus_timer()
        try:
            await self._async_refresh_storm_weather()
            await self._async_refresh_solcast_pv()
            if self._octopus_native_active():
                await self._async_refresh_octopus()
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

        self._solcast_cache = await async_refresh_solcast(
            self.hass, self.plant, self._solcast_cache, force=force
        )
        if (
            self._solcast_store
            and self._solcast_cache.get("pv_forecast_parsed")
        ):
            self._solcast_history_count = await self._solcast_store.async_record_poll(
                self._solcast_cache
            )
            await self._safe_archive_solcast_daily_forecasts()
            await self._rebuild_solcast_forecast_chart()
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
                storm_types=cfg.storm_google_types,
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
        from .panel_config import is_google_weather_alert_entity
        from .storm_weather import is_storm_google_alert_active

        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        if state.state.lower() not in TRIGGER_ON_STATES:
            return False
        if is_google_weather_alert_entity(self.hass, entity_id):
            return is_storm_google_alert_active(
                self.hass,
                entity_id,
                self.plant.storm_prep.storm_weather_categories,
            )
        return True

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
        from .panel_config import resolve_google_weather_entry
        from .storm_weather import read_condition_snapshot, storm_weather_category_catalog

        cfg = self.plant.storm_prep
        out = cfg.to_dict()
        out["weather_provider"] = "google_weather"
        gw = resolve_google_weather_entry(self.hass, cfg.google_weather_entry_id)
        out["storm_weather_category_catalog"] = storm_weather_category_catalog(
            alerts_supported=bool(gw.get("alerts_supported")),
            condition_supported=bool(gw.get("condition_supported")),
        )
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
            forecast_intraday_points=self._solcast_forecast_chart_points,
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
            "tariff": self._tariff_state(),
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
            try:
                await apply_charge_periods(
                    self.hass,
                    self.plant.inverter_target,
                    periods,
                    entity_map=self.plant.entity_map,
                )
            except HomeAssistantError as err:
                if is_charge_period_modbus_blocked(err) and periods_want_grid_force_charge(periods):
                    _LOGGER.warning(
                        "Charge-period Modbus write blocked; using Remote Control Force Charge instead"
                    )
                    await set_remote_control_mode(
                        self.hass, self.plant.entity_map, "Force Charge"
                    )
                    self._fire(
                        EVENT_PERIOD_APPLIED,
                        {
                            "mode": self.plant.plant_mode(),
                            "periods": [p.to_dict() for p in periods],
                            "fallback": "remote_control_force_charge",
                        },
                    )
                    return
                if is_charge_period_modbus_blocked(err):
                    if not periods_want_grid_force_charge(periods):
                        try:
                            await set_remote_control_mode(
                                self.hass, self.plant.entity_map, "Disable"
                            )
                        except HomeAssistantError as rc_err:
                            _LOGGER.debug("Remote Control disable skipped: %s", rc_err)
                    _LOGGER.warning(
                        "Charge-period Modbus write blocked on this EVO firmware (registers read-only): %s",
                        err,
                    )
                    self._fire(
                        EVENT_PERIOD_APPLIED,
                        {
                            "mode": self.plant.plant_mode(),
                            "periods": [p.to_dict() for p in periods],
                            "skipped": "charge_period_modbus_readonly",
                        },
                    )
                    return
                raise
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

    @staticmethod
    def _normalize_period_time(state: str | None) -> str:
        if not state or state in ("unknown", "unavailable"):
            return "00:00"
        parts = state.split(":")
        if len(parts) >= 2:
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        return "00:00"

    def _charge_periods_from_inverter(self) -> list[ChargePeriodConfig]:
        periods = [
            ChargePeriodConfig.from_dict(
                {
                    "enable_force_charge": raw["enable_force_charge"],
                    "enable_charge_from_grid": raw["enable_charge_from_grid"],
                    "start": self._normalize_period_time(raw.get("start")),
                    "end": self._normalize_period_time(raw.get("end")),
                }
            )
            for raw in self._read_actual_periods()
        ]
        while len(periods) < 2:
            periods.append(ChargePeriodConfig())
        return periods[:2]

    async def async_sync_schedule_from_inverter(self) -> None:
        """Copy the inverter's live charge windows into Fox Plant baseline settings."""
        periods = self._charge_periods_from_inverter()
        self.plant.baseline_periods = periods
        await self._persist()
        await self.async_request_refresh()
        _LOGGER.info("Synced baseline charge periods from inverter: %s", [p.to_dict() for p in periods])

    async def async_reapply_schedule(self) -> None:
        """Push Fox Plant's desired schedule to the inverter and enable control if needed."""
        if not self.plant.control_active:
            self.plant.control_active = True
            await self._persist()
        await self.async_apply_desired(force=True)

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
        storm_weather_categories: list[str] | None = None,
    ) -> None:
        """Persist storm prep from the Fox Plant panel."""
        from .panel_config import resolve_google_weather_entry
        from .storm_weather import filter_supported_storm_categories, google_types_from_categories

        periods = [ChargePeriodConfig.from_dict(p) for p in charge_periods]
        triggers = list(trigger_entities)
        use_weather_condition = True
        use_forecast = True if use_forecast_lead is None else use_forecast_lead
        lead_hours = 4 if forecast_lead_hours is None else max(1, min(int(forecast_lead_hours), 48))
        condition_entity_id: str | None = None
        weather_entity_id: str | None = None
        alerts_supported = False
        condition_supported = False
        if google_weather_entry_id:
            sources = resolve_google_weather_entry(self.hass, google_weather_entry_id)
            if sources["alert_trigger_ids"]:
                triggers = sources["alert_trigger_ids"]
            condition_entity_id = sources["condition_entity_id"]
            weather_entity_id = sources["weather_entity_id"]
            alerts_supported = bool(sources.get("alerts_supported"))
            condition_supported = bool(sources.get("condition_supported"))
            use_weather_condition = bool(condition_entity_id)
            if use_forecast_lead is None:
                use_forecast = bool(weather_entity_id)
        filtered_categories = storm_weather_categories
        if google_weather_entry_id:
            filtered_categories = filter_supported_storm_categories(
                storm_weather_categories,
                alerts_supported=alerts_supported,
                condition_supported=condition_supported,
            )
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
        storm_google_types = google_types_from_categories(filtered_categories)
        if filtered_categories is not None:
            storm_data["storm_weather_categories"] = list(filtered_categories)
        if storm_google_types is not None:
            storm_data["storm_google_types"] = storm_google_types
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

    async def async_save_tariff(self, *, tariff: dict[str, Any]) -> None:
        """Persist electricity tariff rates from the panel."""
        from homeassistant.util import dt as dt_util

        from .tariff_rates import TARIFF_SOURCE_ENTITY, resolve_tariff_rates
        from .tariff_store import TariffRateStore

        cfg = TariffConfig.from_dict(tariff)
        for label, source, entity_id in (
            ("Import", cfg.import_source, cfg.import_entity),
            ("Export", cfg.export_source, cfg.export_entity),
            ("Standing charge", cfg.standing_source, cfg.standing_entity),
        ):
            if source != TARIFF_SOURCE_ENTITY or not entity_id:
                continue
            st = self.hass.states.get(entity_id)
            if st is None:
                raise HomeAssistantError(f"{label} entity {entity_id} is not available")
            if not entity_id.startswith("sensor."):
                raise HomeAssistantError(f"{label} entity {entity_id} must be a sensor")
        cfg.last_updated_at = dt_util.utcnow().isoformat()
        data = dict(self.config_entry.data)
        data[CONF_TARIFF] = cfg.to_dict(include_secrets=True)
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        if self._tariff_store is None:
            self._tariff_store = TariffRateStore(self.hass, self.config_entry.entry_id)
        resolved = resolve_tariff_rates(
            self.hass, cfg, entry_id=self.config_entry.entry_id
        )
        effective = resolved["effective"]
        from .tariff_rates import TARIFF_SOURCE_PLUGIN, TARIFF_SOURCE_SCHEDULE

        source_kind = cfg.kind
        sources = {cfg.import_source, cfg.export_source, cfg.standing_source}
        if TARIFF_SOURCE_ENTITY in sources:
            source_kind = "entity" if sources == {TARIFF_SOURCE_ENTITY} else "mixed"
        elif TARIFF_SOURCE_SCHEDULE in sources or TARIFF_SOURCE_PLUGIN in sources:
            source_kind = "schedule"
        self._tariff_history_count = await self._tariff_store.async_record_rates(
            rates=cfg.rates_snapshot(effective=effective),
            source=source_kind,
            recorded_at=cfg.last_updated_at,
        )
        try:
            await self.async_update_tariff_sensors(record_history=False)
        except Exception:
            _LOGGER.exception("Tariff plugin sensor update failed after save")
        self._setup_tariff_schedule_timer()
        self._setup_octopus_timer()
        await self.async_request_refresh()

    async def async_save_octopus(
        self,
        *,
        dynamic: dict[str, Any],
        fetch_now: bool = True,
        apply_schedule: bool = False,
    ) -> None:
        """Persist Octopus dynamic tariff settings from the panel."""
        from .octopus_tariff import OCTOPUS_PROVIDER, OCTOPUS_SOURCE_ENTITY, OCTOPUS_SOURCE_NATIVE
        from .tariff_rates import TARIFF_SOURCE_ENTITY

        fetch_now = bool(dynamic.pop("fetch_now", fetch_now))
        apply_schedule = bool(dynamic.pop("apply_schedule", apply_schedule))
        current = self.plant.tariff.dynamic.to_dict(include_api_key=True)
        merged = {**current, **dynamic}
        if "api_key" in dynamic:
            raw_key = dynamic.get("api_key")
            if raw_key and str(raw_key).strip() and str(raw_key) not in ("********", "••••••••"):
                merged["api_key"] = str(raw_key).strip()
            else:
                merged["api_key"] = current.get("api_key")
        if merged.get("enabled") and not merged.get("provider"):
            merged["provider"] = OCTOPUS_PROVIDER
        cfg = TariffConfig.from_dict(self.plant.tariff.to_dict(include_secrets=True))
        cfg.dynamic = TariffDynamicConfig.from_dict(merged)
        if cfg.dynamic.enabled and cfg.dynamic.source == OCTOPUS_SOURCE_NATIVE:
            if not cfg.dynamic.api_key_configured():
                raise HomeAssistantError("Octopus API key is required for native mode")
            if not cfg.dynamic.account_number:
                raise HomeAssistantError("Octopus account number is required (e.g. A-12345678)")
        elif cfg.dynamic.enabled and cfg.dynamic.source == OCTOPUS_SOURCE_ENTITY:
            if not cfg.dynamic.import_entity and not cfg.dynamic.export_entity:
                raise HomeAssistantError(
                    "Choose at least one external import or export rate sensor for entity mode"
                )
            if cfg.dynamic.import_entity:
                cfg.import_source = TARIFF_SOURCE_ENTITY
                cfg.import_entity = cfg.dynamic.import_entity
            if cfg.dynamic.export_entity:
                cfg.export_source = TARIFF_SOURCE_ENTITY
                cfg.export_entity = cfg.dynamic.export_entity
            cfg.kind = "dynamic"
        from homeassistant.util import dt as dt_util

        cfg.last_updated_at = dt_util.utcnow().isoformat()
        data = dict(self.config_entry.data)
        data[CONF_TARIFF] = cfg.to_dict(include_secrets=True)
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        if fetch_now and cfg.dynamic.native_octopus():
            await self._async_refresh_octopus()
            if apply_schedule and self._octopus_cache.get("schedule"):
                await self.async_apply_octopus_schedule()
            elif self._octopus_agile_active():
                cfg = TariffConfig.from_dict(self.plant.tariff.to_dict(include_secrets=True))
                cfg.kind = "dynamic"
                data = dict(self.config_entry.data)
                data[CONF_TARIFF] = cfg.to_dict(include_secrets=True)
                self.hass.config_entries.async_update_entry(self.config_entry, data=data)
                self.update_plant_config(PlantConfig.from_entry_data(data))
                await self.async_update_tariff_sensors(record_history=True)
        self._setup_tariff_schedule_timer()
        self._setup_octopus_timer()
        await self.async_request_refresh()

    async def async_test_octopus(
        self,
        *,
        api_key: str | None = None,
        account_number: str | None = None,
    ) -> dict[str, Any]:
        from .octopus_api import OctopusApiClient, OctopusApiError
        from .octopus_tariff import test_octopus_connection

        dyn = self.plant.tariff.dynamic
        key = (api_key or dyn.api_key or "").strip()
        account = (account_number or dyn.account_number or "").strip()
        if not key:
            raise HomeAssistantError("Octopus API key is required")
        if not account:
            raise HomeAssistantError("Octopus account number is required")
        client = OctopusApiClient(self.hass, api_key=key)
        try:
            result = await test_octopus_connection(client, account_number=account)
            self._octopus_cache["import_meters"] = result.get("import_meters") or []
            self._octopus_cache["export_meters"] = result.get("export_meters") or []
            return result
        except OctopusApiError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_fetch_octopus(self) -> dict[str, Any]:
        await self._async_refresh_octopus()
        if self._octopus_agile_active():
            await self.async_update_tariff_sensors(record_history=True)
        self._setup_octopus_timer()
        await self.async_request_refresh()
        return self._octopus_status()

    async def async_apply_octopus_schedule(self) -> dict[str, Any]:
        """Apply the last fetched fixed-tariff schedule to tariff config."""
        from .const import TARIFF_KIND_STATIC
        from .octopus_tariff import is_variable_tariff_type
        from .tariff_schedule import TariffScheduleConfig

        schedule_raw = self._octopus_cache.get("schedule")
        if not schedule_raw:
            raise HomeAssistantError("No Octopus schedule available — fetch rates first")
        tariff_type = str(self._octopus_cache.get("tariff_type") or "")
        if is_variable_tariff_type(tariff_type):
            raise HomeAssistantError(
                f"{tariff_type.title()} tariffs use live half-hourly rates, not a daily schedule"
            )
        schedule = TariffScheduleConfig.from_dict(schedule_raw)
        cfg = TariffConfig.from_dict(self.plant.tariff.to_dict(include_secrets=True))
        cfg.schedule = schedule
        cfg.kind = TARIFF_KIND_STATIC
        standing = self._octopus_cache.get("import_standing_p_per_day")
        if standing is not None:
            cfg.standing_charge_p_per_day = max(0.0, float(standing))
        from homeassistant.util import dt as dt_util

        cfg.last_updated_at = dt_util.utcnow().isoformat()
        data = dict(self.config_entry.data)
        data[CONF_TARIFF] = cfg.to_dict(include_secrets=True)
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        await self.async_update_tariff_sensors(record_history=True)
        self._setup_tariff_schedule_timer()
        await self.async_request_refresh()
        return self._tariff_state()

    async def _async_refresh_octopus(self) -> None:
        from .octopus_api import OctopusApiClient, OctopusApiError
        from .octopus_tariff import fetch_octopus_tariff_snapshot, list_account_meters

        dyn = self.plant.tariff.dynamic
        if not dyn.native_octopus():
            return
        if not dyn.api_key_configured() or not dyn.account_number:
            self._octopus_cache["last_error"] = "Octopus API key and account number required"
            return
        client = OctopusApiClient(self.hass, api_key=str(dyn.api_key))
        try:
            snapshot = await fetch_octopus_tariff_snapshot(
                client,
                account_number=str(dyn.account_number),
                import_mpan=dyn.import_mpan,
                export_mpan=dyn.export_mpan,
            )
            self._octopus_cache = snapshot.to_cache_dict()
            try:
                account = await client.get_account(str(dyn.account_number))
                import_meters, export_meters = list_account_meters(account)
                self._octopus_cache["import_meters"] = [
                    {
                        "mpan": m.mpan,
                        "serial": m.serial,
                        "tariff_code": m.tariff_code,
                        "display_name": m.display_name,
                    }
                    for m in import_meters
                ]
                self._octopus_cache["export_meters"] = [
                    {
                        "mpan": m.mpan,
                        "serial": m.serial,
                        "tariff_code": m.tariff_code,
                        "display_name": m.display_name,
                    }
                    for m in export_meters
                ]
            except OctopusApiError:
                pass
            _LOGGER.debug(
                "Octopus tariff refreshed (%s, import %s)",
                snapshot.tariff_type,
                snapshot.import_meter.tariff_code if snapshot.import_meter else "—",
            )
        except OctopusApiError as err:
            self._octopus_cache["last_error"] = str(err)
            _LOGGER.warning("Octopus tariff fetch failed: %s", err)

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
            forecast_intraday_points=self._solcast_forecast_chart_points,
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
        if getattr(self, "_unsub_tariff_schedule", None):
            self._unsub_tariff_schedule()
            self._unsub_tariff_schedule = None
        if getattr(self, "_unsub_octopus", None):
            self._unsub_octopus()
            self._unsub_octopus = None
