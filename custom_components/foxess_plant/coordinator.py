"""Plant coordinator — central control for charge periods and drift detection."""

from __future__ import annotations

import asyncio
import logging
import time
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
    CONF_SMART_CHARGE,
    CONF_SOLCAST,
    CONF_GLOW,
    CONF_STORM_PREP,
    CONF_TARIFF,
    IDENTITY_ENTITY_SUFFIXES,
    SOLCAST_FORECAST_HISTORY_MAX,
    EVENT_BASELINE_RESTORED,
    EVENT_CONTROL_DRIFT,
    EVENT_EXTERNAL_WRITE,
    EVENT_FORECAST_ARMED,
    EVENT_FORECAST_DISARMED,
    EVENT_SMART_CHARGE_ARMED,
    EVENT_SMART_CHARGE_DISARMED,
    EVENT_OUTAGE_ARMED,
    EVENT_OUTAGE_DISARMED,
    EVENT_PERIOD_APPLIED,
    EVENT_PERIOD_APPLY_FAILED,
    EVENT_STORM_ARMED,
    EVENT_STORM_DISARMED,
    EVENT_TARIFF_APPLIED,
    MODE_FORECAST,
    MODE_OUTAGE,
    MODE_SMART_CHARGE,
    MODE_STORM,
    MODE_TARIFF,
    TRANSIENT_WORK_MODE_OPTIONS,
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
    GlowConfig,
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
        self._smart_charge_armed = False
        self._smart_charge_discharge_armed = False
        self._smart_charge_decision: dict[str, Any] = {}
        self._smart_charge_daily_plan: list[dict[str, Any]] = []
        self._smart_charge_periods_sig = ""
        self._smart_charge_discharge_sig = ""
        self._smart_charge_rates_snapshot: list[tuple[str, float]] = []
        self._storm_forecast_active = False
        self._storm_forecast_detail = {}
        self._solcast_cache: dict[str, Any] = {}
        self._solcast_store = None
        self._solcast_storage_load_failed = False
        self._solcast_storage_last_fail_monotonic = 0.0
        self._solcast_stored_snapshot: dict[str, Any] = {}
        self._solcast_history_count = 0
        self._solcast_forecast_chart_points: list[dict[str, float]] = []
        self._solcast_memory_snapshots: list[tuple[float, list[dict[str, Any]]]] = []
        self._solcast_refresh_lock = asyncio.Lock()
        self._solcast_store_lock = asyncio.Lock()
        self._solcast_empty_fetch_attempted = False
        self._tariff_store = None
        self._tariff_history_count = 0
        self._tariff_rate_sensors: dict[str, Any] = {}
        self._unsub_tariff_schedule: callable | None = None
        self._unsub_octopus: callable | None = None
        self._unsub_smart_charge: callable | None = None
        self._unsub_smart_charge_daily_plan: callable | None = None
        self._unsub_smart_charge_entity: callable | None = None
        self._unsub_pv_efficiency: callable | None = None
        self._last_tariff_sensor_rates: dict[str, float] = {}
        self._octopus_cache: dict[str, Any] = {}
        self._octopus_greener_store = None
        self._octopus_greener_cache: dict[str, Any] = {}
        self._octopus_greener_history_count = 0
        self._octopus_greener_history: list[dict[str, Any]] = []
        self._octopus_analysis_cache: dict[str, Any] = {}
        self._octopus_consumption_store = None
        self._octopus_consumption_data: dict[str, Any] = {}
        self._octopus_consumption_sensors: dict[str, Any] = {}
        self._unsub_octopus_consumption: callable | None = None
        self._unsub_octopus_greener: callable | None = None
        self._octopus_rate_limited_until = None
        self._glow_live: dict[str, Any] = {}
        self._glow_unsub_mqtt: callable | None = None
        self._glow_sensors: dict[str, Any] = {}
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"FoxESS Plant {entry.title}",
            update_interval=UPDATE_INTERVAL,
        )

    def _remember_solcast_stored(self, stored: dict[str, Any] | None) -> dict[str, Any]:
        if isinstance(stored, dict):
            self._solcast_stored_snapshot = stored
            return stored
        return self._solcast_stored_snapshot

    def _append_solcast_memory_snapshot(self) -> None:
        """Keep in-memory poll history when .storage reads fail."""
        rows = self._solcast_detailed_forecast_rows()
        if len(rows) < 2:
            return
        from .solcast_forecast_chart import _parse_fetched_at_ms

        fetched_ms = _parse_fetched_at_ms(
            self._solcast_cache.get("updated_at")
            or self._solcast_cache.get("pv_forecast_fetched_at")
        )
        if fetched_ms is None:
            fetched_ms = time.time() * 1000
        key = float(fetched_ms)
        rows_copy = list(rows)
        for index, (ms, _) in enumerate(self._solcast_memory_snapshots):
            if abs(ms - key) < 1000:
                self._solcast_memory_snapshots[index] = (key, rows_copy)
                return
        self._solcast_memory_snapshots.append((key, rows_copy))
        if len(self._solcast_memory_snapshots) > SOLCAST_FORECAST_HISTORY_MAX:
            self._solcast_memory_snapshots = self._solcast_memory_snapshots[
                -SOLCAST_FORECAST_HISTORY_MAX:
            ]

    def _restore_solcast_memory_from_stored(self, stored: dict[str, Any]) -> None:
        """Rebuild in-memory poll history after a successful .storage load."""
        from .solcast_forecast_chart import _detailed_rows, _parse_fetched_at_ms
        from .solcast_store import _snapshot_has_forecast

        merged: dict[float, list[dict[str, Any]]] = {}
        history = stored.get("history") if isinstance(stored, dict) else None
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                cache = item.get("cache")
                if not _snapshot_has_forecast(cache):
                    continue
                fetched_ms = _parse_fetched_at_ms(item.get("fetched_at"))
                if fetched_ms is None:
                    fetched_ms = _parse_fetched_at_ms(
                        (cache or {}).get("updated_at")
                        or (cache or {}).get("pv_forecast_fetched_at")
                    )
                rows = _detailed_rows(cache)
                if fetched_ms is not None and len(rows) >= 2:
                    merged[float(fetched_ms)] = list(rows)
        if _snapshot_has_forecast(self._solcast_cache):
            fetched_ms = _parse_fetched_at_ms(
                self._solcast_cache.get("updated_at")
                or self._solcast_cache.get("pv_forecast_fetched_at")
            )
            rows = self._solcast_detailed_forecast_rows()
            if fetched_ms is not None and len(rows) >= 2:
                merged[float(fetched_ms)] = list(rows)
        self._solcast_memory_snapshots = sorted(merged.items(), key=lambda item: item[0])[
            -SOLCAST_FORECAST_HISTORY_MAX:
        ]

    def _stored_from_memory_snapshots(self) -> dict[str, Any]:
        """Synthesize a .storage-shaped document from in-memory poll history."""
        from homeassistant.util import dt as dt_util

        from .solcast_forecast_chart import _utc_from_timestamp

        if not self._solcast_memory_snapshots:
            return {}
        history: list[dict[str, Any]] = []
        for fetched_ms, rows in self._solcast_memory_snapshots:
            when = dt_util.as_local(_utc_from_timestamp(fetched_ms / 1000))
            fetched_at = when.isoformat()
            history.append(
                {
                    "fetched_at": fetched_at,
                    "cache": {
                        "updated_at": fetched_at,
                        "pv_forecast_parsed": {"detailed_forecast": list(rows)},
                    },
                }
            )
        current = self._solcast_cache if self._solcast_detailed_forecast_rows() else None
        if current is None and self._solcast_memory_snapshots:
            fetched_ms, rows = self._solcast_memory_snapshots[-1]
            when = dt_util.as_local(_utc_from_timestamp(fetched_ms / 1000))
            fetched_at = when.isoformat()
            current = {
                "updated_at": fetched_at,
                "pv_forecast_fetched_at": fetched_at,
                "pv_forecast_parsed": {"detailed_forecast": list(rows)},
            }
        return {
            "version": 1,
            "current": current,
            "history": history,
            "daily_intraday": dict(
                (self._solcast_stored_snapshot or {}).get("daily_intraday") or {}
            ),
        }

    def _restore_solcast_cache_from_memory(self) -> bool:
        """Rebuild coordinator forecast cache from in-memory poll history."""
        from .solcast_store import _snapshot_has_forecast, cache_from_storage

        if len(self._solcast_detailed_forecast_rows()) >= 2:
            return True
        if not self._solcast_memory_snapshots:
            return False
        stored = self._stored_from_memory_snapshots()
        cache = cache_from_storage(stored)
        if not _snapshot_has_forecast(cache):
            return False
        self._solcast_cache = cache
        self._enrich_solcast_cache_metrics()
        _LOGGER.debug("Restored Solcast forecast cache from in-memory poll history")
        return True

    async def _async_load_solcast_store_document(self) -> dict[str, Any]:
        """Load HA .storage under lock; returns last good snapshot on failure."""
        if self._solcast_stored_snapshot:
            return self._solcast_stored_snapshot
        if not await self._ensure_solcast_store():
            if self._solcast_memory_snapshots:
                return self._remember_solcast_stored(self._stored_from_memory_snapshots())
            return {}
        async with self._solcast_store_lock:
            if self._solcast_stored_snapshot:
                return self._solcast_stored_snapshot
            for attempt in range(2):
                try:
                    stored = await self._solcast_store.async_load()
                    stored = stored if isinstance(stored, dict) else {}
                    self._solcast_storage_load_failed = False
                    remembered = self._remember_solcast_stored(stored)
                    self._restore_solcast_memory_from_stored(remembered)
                    return remembered
                except Exception:
                    if attempt == 0:
                        await asyncio.sleep(0.05)
                        continue
                    self._solcast_storage_load_failed = True
                    self._solcast_storage_last_fail_monotonic = time.monotonic()
                    if self._solcast_memory_snapshots:
                        _LOGGER.warning(
                            "Solcast forecast store read failed; using in-memory poll history"
                        )
                        return self._remember_solcast_stored(
                            self._stored_from_memory_snapshots()
                        )
                    _LOGGER.exception("Solcast forecast store read failed")
                    return self._solcast_stored_snapshot

    async def async_read_solcast_stored(self) -> dict[str, Any]:
        """Read HA .storage document; never raises (websocket-safe)."""
        return await self._async_load_solcast_store_document()

    async def _ensure_solcast_store(self) -> bool:
        """Open the HA .storage handle when missing (e.g. after a prior load failure)."""
        if self._solcast_store:
            return True
        from .solcast_store import SolcastForecastStore

        try:
            self._solcast_store = SolcastForecastStore(self.hass, self.config_entry.entry_id)
            self._solcast_storage_load_failed = False
            return True
        except Exception:
            _LOGGER.exception("Could not open Solcast forecast store")
            self._solcast_store = None
            self._solcast_storage_load_failed = True
            self._solcast_storage_last_fail_monotonic = time.monotonic()
            return False

    async def _async_load_solcast_storage(self) -> None:
        """Restore forecast cache from HA .storage (parsed + raw API documents)."""
        from .solcast_store import SolcastForecastStore, cache_from_storage

        if not await self._ensure_solcast_store():
            return

        stored = await self._async_load_solcast_store_document()
        stored = self._remember_solcast_stored(stored)
        if stored:
            self._restore_solcast_memory_from_stored(stored)

        try:
            self._solcast_cache = cache_from_storage(stored)
            if len(self._solcast_detailed_forecast_rows()) < 2:
                self._restore_solcast_cache_from_memory()
            self._enrich_solcast_cache_metrics()
            self._solcast_history_count = SolcastForecastStore.history_count(stored)
            self._solcast_storage_load_failed = False
            if self._solcast_detailed_forecast_rows():
                _LOGGER.debug(
                    "Restored Solcast forecast from storage (%s history snapshots)",
                    self._solcast_history_count,
                )
                try:
                    await self._maybe_repair_solcast_storage(stored)
                except Exception:
                    _LOGGER.exception("Solcast storage repair failed")
        except Exception:
            _LOGGER.exception("Solcast cache restore failed; keeping store handle open")
            self._solcast_storage_load_failed = True

        try:
            await self._rebuild_solcast_forecast_chart(stored=stored)
        except Exception:
            _LOGGER.exception("Solcast forecast chart rebuild failed after storage load")

        self.hass.async_create_task(self._safe_archive_solcast_daily_forecasts())

    async def _safe_archive_solcast_daily_forecasts(self) -> None:
        """Archive daily charts without blocking or breaking coordinator startup."""
        try:
            await self._archive_solcast_daily_forecasts()
        except Exception:
            _LOGGER.debug("Solcast daily forecast archive failed", exc_info=True)

    async def _archive_solcast_daily_forecasts(self) -> None:
        """Persist per-day forecast chart lines so Analysis can show past days."""
        if not self._solcast_store:
            return
        from .solcast_forecast_chart import archive_daily_intraday_forecasts

        stored = await self._async_load_solcast_store_document()
        updates = await self.hass.async_add_executor_job(
            archive_daily_intraday_forecasts,
            self.hass,
            stored,
            self._solcast_cache,
            entry_id=self.config_entry.entry_id,
            use_recorder=False,
        )
        if updates:
            try:
                async with self._solcast_store_lock:
                    await self._solcast_store.async_merge_daily_intraday(updates)
                    try:
                        loaded = await self._solcast_store.async_load()
                        self._remember_solcast_stored(
                            loaded if isinstance(loaded, dict) else {}
                        )
                    except Exception:
                        synth = self._stored_from_memory_snapshots()
                        if synth:
                            self._remember_solcast_stored(synth)
                        _LOGGER.debug(
                            "Solcast daily archive store re-read skipped",
                            exc_info=True,
                        )
                _LOGGER.debug(
                    "Archived Solcast daily forecast charts for %s",
                    ", ".join(sorted(updates.keys())),
                )
            except Exception:
                _LOGGER.debug("Solcast daily forecast archive skipped", exc_info=True)

    async def _async_load_tariff_storage(self) -> None:
        from .tariff_store import TariffRateStore
        from .octopus_greener_store import OctopusGreenerStore
        from .octopus_consumption_store import OctopusConsumptionStore

        self._tariff_store = TariffRateStore(self.hass, self.config_entry.entry_id)
        stored = await self._tariff_store.async_load()
        self._tariff_history_count = TariffRateStore.history_count(stored)
        self._octopus_greener_store = OctopusGreenerStore(self.hass, self.config_entry.entry_id)
        greener_stored = await self._octopus_greener_store.async_load()
        self._octopus_greener_history_count = OctopusGreenerStore.history_count(greener_stored)
        self._octopus_greener_history = OctopusGreenerStore.history_entries(greener_stored)
        current = greener_stored.get("current") if isinstance(greener_stored, dict) else None
        if isinstance(current, dict) and isinstance(current.get("snapshot"), dict):
            from .octopus_greener import hydrate_greener_snapshot_from_history

            self._octopus_greener_cache = hydrate_greener_snapshot_from_history(
                dict(current["snapshot"]),
                self._octopus_greener_history,
            )
        self._octopus_consumption_store = OctopusConsumptionStore(
            self.hass, self.config_entry.entry_id
        )
        cons_stored = await self._octopus_consumption_store.async_load()
        import_rows = list(cons_stored.get("import") or [])
        compliance = None
        if import_rows and self._octopus_greener_cache.get("greener_nights"):
            from .octopus_analysis import compute_greener_compliance

            compliance = compute_greener_compliance(
                import_rows,
                list(self._octopus_greener_cache.get("greener_nights") or []),
            )
        self._octopus_consumption_data = {
            "import": import_rows,
            "export": list(cons_stored.get("export") or []),
            "last_fetch_at": cons_stored.get("last_fetch_at"),
            "compliance": compliance,
            "errors": {},
        }
        if self._octopus_greener_enabled() and self._octopus_greener_cache:
            await self._async_refresh_octopus_analysis()

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
        state["octopus_greener"] = self._octopus_greener_state()
        state["octopus_analysis"] = self._octopus_analysis_state()
        return state

    def register_octopus_consumption_sensor(self, kind: str, sensor: Any) -> None:
        self._octopus_consumption_sensors[kind] = sensor

    async def async_update_octopus_consumption_sensors(self) -> None:
        from .octopus_analysis import octopus_consumption_sensor_values

        if not self._octopus_greener_enabled():
            return
        values = octopus_consumption_sensor_values(
            list(self._octopus_consumption_data.get("import") or []),
            self._octopus_consumption_data.get("compliance"),
        )
        mapping = {
            "half_hour": values.get("half_hour_kwh"),
            "today": values.get("today_kwh"),
            "greener_alignment": values.get("greener_alignment_pct"),
        }
        for kind, value in mapping.items():
            sensor = self._octopus_consumption_sensors.get(kind)
            if sensor is None:
                continue
            sensor.set_value(value)
            await sensor.async_publish()

    def _octopus_greener_enabled(self) -> bool:
        from .octopus_greener import octopus_tariff_enabled

        return octopus_tariff_enabled(self.plant.tariff)

    def _octopus_greener_state(self) -> dict[str, Any] | None:
        if not self._octopus_greener_enabled():
            return None
        from .octopus_greener import greener_dashboard_payload, hydrate_greener_snapshot_from_history

        cache = hydrate_greener_snapshot_from_history(
            dict(self._octopus_greener_cache or {}),
            self._octopus_greener_history,
        )
        return greener_dashboard_payload(
            cache,
            history_count=self._octopus_greener_history_count,
            current_import_p_per_kwh=self._octopus_cache.get("current_import_p_per_kwh"),
        )

    def _octopus_analysis_state(self) -> dict[str, Any] | None:
        if not self._octopus_greener_enabled():
            return None
        from .octopus_analysis import octopus_analysis_dashboard_payload

        return octopus_analysis_dashboard_payload(
            self._octopus_analysis_cache,
            greener_payload=self._octopus_greener_state(),
        )

    def _octopus_native_active(self) -> bool:
        return self.plant.tariff.dynamic.native_octopus() and self.plant.tariff.dynamic.api_key_configured()

    def _octopus_agile_active(self) -> bool:
        from .octopus_tariff import is_variable_tariff_type

        if not self._octopus_native_active():
            return False
        tariff_type = self._octopus_cache.get("tariff_type")
        return bool(tariff_type and is_variable_tariff_type(str(tariff_type)))

    def _octopus_entity_active(self) -> bool:
        return self.plant.tariff.dynamic.entity_octopus()

    def _smart_charge_tariff_type(self) -> str | None:
        if self._octopus_native_active():
            raw = self._octopus_cache.get("tariff_type")
            return str(raw) if raw else None
        if not self._octopus_entity_active():
            return None
        from .octopus_tariff import classify_tariff_code
        from .smart_charge.entity_rates import tariff_code_from_attributes

        dyn = self.plant.tariff.dynamic
        code = None
        if dyn.import_entity:
            state = self.hass.states.get(dyn.import_entity)
            if state:
                code = tariff_code_from_attributes(state.attributes)
        if code:
            return classify_tariff_code(code)
        return None

    def _octopus_tracker_active(self) -> bool:
        from .octopus_tariff import is_tracker_tariff_type

        return is_tracker_tariff_type(self._smart_charge_tariff_type())

    def _smart_charge_poll_interval_minutes(self) -> int:
        cfg = self.plant.smart_charge
        base = max(5, min(60, int(cfg.agile_poll_interval_minutes or 15)))
        if self._octopus_tracker_active():
            return max(base, 60)
        return base

    def _smart_charge_entity_rate_rows(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        from .smart_charge.entity_rates import collect_rate_rows_from_attributes, merge_rate_rows

        dyn = self.plant.tariff.dynamic
        import_rows: list[dict[str, Any]] = []
        export_rows: list[dict[str, Any]] = []
        if dyn.import_entity:
            state = self.hass.states.get(dyn.import_entity)
            if state:
                import_rows = merge_rate_rows(collect_rate_rows_from_attributes(state.attributes))
        if dyn.export_entity:
            state = self.hass.states.get(dyn.export_entity)
            if state:
                export_rows = merge_rate_rows(collect_rate_rows_from_attributes(state.attributes))
        return import_rows, export_rows

    def _octopus_parse_iso_age(self, iso: str | None) -> timedelta | None:
        if not iso:
            return None
        from homeassistant.util import dt as dt_util

        parsed = dt_util.parse_datetime(str(iso))
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt_util.UTC)
        return dt_util.utcnow() - parsed

    def _octopus_rate_limited(self) -> bool:
        until = self._octopus_rate_limited_until
        if until is None:
            return False
        from homeassistant.util import dt as dt_util

        return dt_util.utcnow() < until

    def _note_octopus_rate_limit(self, *messages: str | None) -> None:
        from .octopus_greener import is_octopus_rate_limit_error
        from homeassistant.util import dt as dt_util

        if not any(is_octopus_rate_limit_error(message) for message in messages if message):
            return
        self._octopus_rate_limited_until = dt_util.utcnow() + timedelta(minutes=30)
        _LOGGER.warning(
            "Octopus API rate limited — pausing refreshes until %s",
            self._octopus_rate_limited_until.isoformat(),
        )

    def _octopus_cache_fresh(self, cache: dict[str, Any], key: str, min_interval: timedelta) -> bool:
        age = self._octopus_parse_iso_age(cache.get(key))
        return age is not None and age < min_interval

    def _octopus_tariff_refresh_due(self, *, force: bool = False) -> bool:
        if force:
            return True
        if self._octopus_rate_limited():
            return False
        if not self._octopus_cache:
            return True
        return not self._octopus_cache_fresh(
            self._octopus_cache, "last_fetch_at", timedelta(minutes=55)
        )

    def _octopus_greener_refresh_due(self, *, force: bool = False) -> bool:
        if force:
            return True
        if self._octopus_rate_limited():
            return False
        if not self._octopus_greener_cache:
            return True
        from .octopus_greener import carbon_periods_current

        cache = self._octopus_greener_cache
        carbon = list(cache.get("carbon_periods") or [])
        greener = list(cache.get("greener_nights") or [])
        if not greener or not carbon_periods_current(carbon):
            interval = timedelta(minutes=15)
        else:
            interval = timedelta(minutes=110)
        return not self._octopus_cache_fresh(cache, "fetched_at", interval)

    def _octopus_consumption_refresh_due(self, *, force: bool = False) -> bool:
        if force:
            return True
        if self._octopus_rate_limited():
            return False
        if not self._octopus_consumption_data.get("import"):
            return True
        return not self._octopus_cache_fresh(
            self._octopus_consumption_data, "last_fetch_at", timedelta(minutes=25)
        )

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
        from .tariff_rates import scheduled_rates_at

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

        agile = self._octopus_agile_active()
        interval = 15
        if agile and self.plant.smart_charge.enabled:
            interval = self._smart_charge_poll_interval_minutes()
        when = next_octopus_poll_boundary(agile=agile, interval_minutes=interval)
        self._unsub_octopus = async_track_point_in_time(self.hass, self._octopus_timer_callback, when)

    @callback
    def _octopus_timer_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_octopus_tick())

    async def _async_octopus_tick(self) -> None:
        cfg = self.plant.smart_charge
        prev_rates = list(self._smart_charge_rates_snapshot)
        await self._async_refresh_octopus()
        self._setup_octopus_timer()
        if self._octopus_agile_active():
            await self.async_update_tariff_sensors(record_history=True)
        from .smart_charge.spread_math import material_import_price_drop, rates_snapshot

        current_rates = rates_snapshot(self._octopus_cache.get("import_rates") or [])
        self._smart_charge_rates_snapshot = current_rates
        price_drop_replan = False
        if cfg.enabled and prev_rates and current_rates and not self._octopus_tracker_active():
            threshold = float(cfg.price_drop_interrupt_p_per_kwh or 2.0)
            price_drop_replan = material_import_price_drop(
                prev_rates, current_rates, threshold_p=threshold
            )
        try:
            if price_drop_replan:
                await self._evaluate_smart_charge_daily_plan()
            else:
                await self._evaluate_smart_charge()
        except Exception as err:
            _LOGGER.warning("Smart charge evaluation failed: %s", err)
        await self.async_request_refresh()

    @callback
    def _tariff_schedule_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_tariff_schedule_tick())

    async def _async_tariff_schedule_tick(self) -> None:
        await self.async_update_tariff_sensors(record_history=True)
        self._setup_tariff_schedule_timer()
        try:
            await self._evaluate_smart_charge()
        except Exception as err:
            _LOGGER.warning("Smart charge evaluation failed: %s", err)
        await self.async_request_refresh()

    def _setup_smart_charge_timer(self) -> None:
        if self._unsub_smart_charge:
            self._unsub_smart_charge()
            self._unsub_smart_charge = None
        if not self.plant.smart_charge.enabled:
            return
        from .octopus_tariff import next_agile_poll_boundary

        interval = self._smart_charge_poll_interval_minutes()
        when = next_agile_poll_boundary(interval_minutes=interval)
        self._unsub_smart_charge = async_track_point_in_time(
            self.hass, self._smart_charge_timer_callback, when
        )

    def _setup_smart_charge_daily_plan_timer(self) -> None:
        if self._unsub_smart_charge_daily_plan:
            self._unsub_smart_charge_daily_plan()
            self._unsub_smart_charge_daily_plan = None
        if not self.plant.smart_charge.enabled:
            return
        from .octopus_tariff import next_daily_smart_charge_plan_boundary

        when = next_daily_smart_charge_plan_boundary(
            plan_time=self.plant.smart_charge.daily_plan_time or "16:00"
        )
        self._unsub_smart_charge_daily_plan = async_track_point_in_time(
            self.hass, self._smart_charge_daily_plan_callback, when
        )

    @callback
    def _smart_charge_daily_plan_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_smart_charge_daily_plan_tick())

    async def _async_smart_charge_daily_plan_tick(self) -> None:
        try:
            await self._evaluate_smart_charge_daily_plan()
        except Exception as err:
            _LOGGER.warning("Smart charge daily plan failed: %s", err)
        self._setup_smart_charge_daily_plan_timer()
        await self.async_request_refresh()

    @callback
    def _smart_charge_timer_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_smart_charge_tick())

    async def _async_smart_charge_tick(self) -> None:
        try:
            if self._octopus_entity_active():
                await self._maybe_replan_smart_charge_on_entity_rates()
            else:
                await self._evaluate_smart_charge()
        except Exception as err:
            _LOGGER.warning("Smart charge evaluation failed: %s", err)
        self._setup_smart_charge_timer()
        await self.async_request_refresh()

    async def _maybe_replan_smart_charge_on_entity_rates(self) -> None:
        from .smart_charge.spread_math import material_import_price_drop, rates_snapshot

        cfg = self.plant.smart_charge
        prev_rates = list(self._smart_charge_rates_snapshot)
        import_rows, _ = self._smart_charge_entity_rate_rows()
        current_rates = rates_snapshot(import_rows)
        self._smart_charge_rates_snapshot = current_rates
        replan = False
        if (
            cfg.enabled
            and prev_rates
            and current_rates
            and not self._octopus_tracker_active()
        ):
            threshold = float(cfg.price_drop_interrupt_p_per_kwh or 2.0)
            replan = material_import_price_drop(prev_rates, current_rates, threshold_p=threshold)
        if replan:
            await self._evaluate_smart_charge_daily_plan()
        else:
            await self._evaluate_smart_charge()

    def _setup_smart_charge_entity_listener(self) -> None:
        if self._unsub_smart_charge_entity:
            self._unsub_smart_charge_entity()
            self._unsub_smart_charge_entity = None
        dyn = self.plant.tariff.dynamic
        if not dyn.entity_octopus() or not self.plant.smart_charge.enabled:
            return
        entities = tuple(entity for entity in (dyn.import_entity, dyn.export_entity) if entity)
        if not entities:
            return

        @callback
        def _on_entity_rate_change(_event: Event) -> None:
            self.hass.async_create_task(self._async_smart_charge_entity_rate_tick())

        self._unsub_smart_charge_entity = async_track_state_change_event(
            self.hass, entities, _on_entity_rate_change
        )

    async def _async_smart_charge_entity_rate_tick(self) -> None:
        try:
            await self._maybe_replan_smart_charge_on_entity_rates()
        except Exception as err:
            _LOGGER.warning("Smart charge entity rate tick failed: %s", err)
        await self.async_request_refresh()

    def _setup_pv_efficiency_timer(self) -> None:
        if self._unsub_pv_efficiency:
            self._unsub_pv_efficiency()
            self._unsub_pv_efficiency = None
        if not self.plant.solcast.installation_date:
            return
        from .pv_efficiency import next_pv_efficiency_check

        when = next_pv_efficiency_check()
        self._unsub_pv_efficiency = async_track_point_in_time(
            self.hass, self._pv_efficiency_timer_callback, when
        )

    @callback
    def _pv_efficiency_timer_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_pv_efficiency_tick())

    async def _async_pv_efficiency_tick(self) -> None:
        try:
            await self._async_apply_pv_efficiency_age_derating(refresh_solcast=True)
        except Exception as err:
            _LOGGER.warning("PV efficiency age sync failed: %s", err)
        self._setup_pv_efficiency_timer()

    async def _async_apply_pv_efficiency_age_derating(
        self, *, refresh_solcast: bool = False
    ) -> bool:
        """Recompute PV efficiency from Solcast install date; persist when it changes."""
        install_date = self.plant.solcast.installation_date
        if not install_date:
            return False
        from .pv_efficiency import sync_pv_efficiency_from_install

        updated, changed = sync_pv_efficiency_from_install(self.plant.pv_config, install_date)
        if not changed:
            return False
        eff = int(round(updated.pv1.efficiency_factor))
        annual = updated.annual_degradation_pct
        data = dict(self.config_entry.data)
        data[CONF_PV_CONFIG] = updated.to_dict()
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        _LOGGER.info(
            "PV efficiency updated to %s%% from installation date %s (annual derating %.2f%%)",
            eff,
            install_date,
            annual,
        )
        if refresh_solcast and self._solcast_pv_active():
            await self._async_refresh_solcast_pv(force=True)
        await self.async_request_refresh()
        return True

    async def _rebuild_solcast_forecast_chart(
        self, *, stored: dict[str, Any] | None = None
    ) -> None:
        from .solcast_forecast_chart import build_forecast_intraday_chart

        if stored is None:
            stored = await self._async_load_solcast_store_document()
        if (
            not stored
            and not self._solcast_memory_snapshots
            and len(self._solcast_detailed_forecast_rows()) < 2
        ):
            self._solcast_forecast_chart_points = []
            return

        entry_id = self.config_entry.entry_id
        memory_snapshots = list(self._solcast_memory_snapshots)
        self._solcast_forecast_chart_points = build_forecast_intraday_chart(
            self.hass,
            stored,
            self._solcast_cache,
            entry_id=entry_id,
            memory_snapshots=memory_snapshots,
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
        async with self._solcast_store_lock:
            from copy import deepcopy

            from .solcast_forecast_metrics import strip_volatile_forecast_metrics

            poll_cache = deepcopy(self._solcast_cache)
            parsed = poll_cache.get("pv_forecast_parsed")
            if isinstance(parsed, dict):
                poll_cache["pv_forecast_parsed"] = strip_volatile_forecast_metrics(parsed)
            self._solcast_history_count = await self._solcast_store.async_record_poll(poll_cache)
            repaired = await self._solcast_store.async_load()
            self._remember_solcast_stored(repaired if isinstance(repaired, dict) else {})
        _LOGGER.info("Repaired Solcast forecast storage from history snapshot")

    def _enrich_solcast_cache_metrics(self) -> None:
        """Refresh time-sensitive Solcast sensor metrics from cached detailed_forecast rows."""
        parsed = self._solcast_cache.get("pv_forecast_parsed")
        if not isinstance(parsed, dict):
            return
        from .solcast_forecast_metrics import apply_forecast_metrics

        self._solcast_cache["pv_forecast_parsed"] = apply_forecast_metrics(parsed, self.hass)

    def _solcast_pv_active(self) -> bool:
        """True when automatic Solcast PV polling is configured (matches async_refresh_solcast gates)."""
        sc = self.plant.solcast
        if not (sc.enabled and sc.api_key_configured() and sc.fetch_pv_forecast):
            return False
        from .solcast_pv import build_rooftop_pv_requests

        return bool(build_rooftop_pv_requests(self.plant.pv_config))

    def _solcast_forecast_covers_now(self) -> bool:
        """True when cached detailed forecast still has a future interval."""
        rows = self._solcast_detailed_forecast_rows()
        if len(rows) < 2:
            return False
        from homeassistant.util import dt as dt_util

        from .solcast_forecast_metrics import _build_intervals

        now = dt_util.now()
        return any(interval.end > now for interval in _build_intervals(rows))

    def _solcast_poll_due(self) -> bool:
        """True when schedule says a poll is due (same logic as panel next-fetch status)."""
        if not self._solcast_pv_active():
            return False
        from .solcast_poll import should_poll_now, solcast_next_fetch
        from .solcast_pv import build_rooftop_pv_requests

        if not should_poll_now(self.hass, self.plant.solcast):
            return False
        pv_calls = max(1, len(build_rooftop_pv_requests(self.plant.pv_config)) or 1)
        next_fetch = solcast_next_fetch(
            self.hass, self.plant.solcast, self._solcast_cache, pv_calls=pv_calls
        )
        return (next_fetch or {}).get("status") == "due_now"

    def _solcast_storage_reload_due(self) -> bool:
        """Throttle storage reload attempts after a read failure."""
        if not self._solcast_storage_load_failed:
            return True
        return (time.monotonic() - self._solcast_storage_last_fail_monotonic) >= 300.0

    async def async_ensure_solcast_cache(self, *, allow_poll: bool = True) -> None:
        """Load persisted forecast; poll only on the normal schedule (never force on empty cache)."""
        if len(self._solcast_detailed_forecast_rows()) < 2:
            if self._solcast_storage_reload_due():
                await self._async_load_solcast_storage()
            if len(self._solcast_detailed_forecast_rows()) < 2:
                self._restore_solcast_cache_from_memory()
        if not allow_poll:
            return
        if len(self._solcast_detailed_forecast_rows()) < 2 and self._solcast_pv_active():
            if not self._solcast_empty_fetch_attempted:
                self._solcast_empty_fetch_attempted = True
                try:
                    await self._async_refresh_solcast_pv(force=True)
                except Exception:
                    _LOGGER.exception("Initial Solcast PV forecast fetch failed")
                if len(self._solcast_detailed_forecast_rows()) >= 2:
                    return
        if self._solcast_forecast_covers_now():
            return
        if self._solcast_poll_due():
            try:
                await self._async_refresh_solcast_pv(force=False)
            except Exception:
                _LOGGER.exception("Opportunistic Solcast PV poll failed")

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
        self._setup_octopus_greener_timer()
        self._setup_octopus_consumption_timer()
        self._setup_glow_mqtt()
        self._setup_smart_charge_timer()
        self._setup_smart_charge_daily_plan_timer()
        self._setup_smart_charge_entity_listener()
        self._setup_pv_efficiency_timer()
        try:
            await self._async_apply_pv_efficiency_age_derating()
        except Exception as err:
            _LOGGER.warning("Initial PV efficiency age sync failed: %s", err)
        try:
            await self._async_refresh_storm_weather()
        except Exception as err:
            _LOGGER.warning("Initial storm weather sync failed: %s", err)
        try:
            if self._octopus_native_active() and self._octopus_tariff_refresh_due():
                await self._async_refresh_octopus()
            elif self._octopus_greener_enabled() and self._octopus_greener_refresh_due():
                await self._async_refresh_octopus_greener()
            if (
                self._octopus_greener_enabled()
                and self.plant.tariff.dynamic.api_key_configured()
                and self._octopus_consumption_refresh_due()
            ):
                await self._async_refresh_octopus_consumption()
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

    async def _async_refresh_solcast_pv(self, *, force: bool = False) -> None:
        """Poll Solcast rooftop PV forecast (Google Weather handles storms/overview)."""
        if not self._solcast_pv_active():
            return
        from .solcast_poll import async_refresh_solcast

        async with self._solcast_refresh_lock:
            try:
                self._solcast_cache = await async_refresh_solcast(
                    self.hass, self.plant, self._solcast_cache, force=force
                )
            except Exception:
                _LOGGER.exception("Solcast PV forecast fetch failed")
                return
            if self._solcast_cache.get("pv_forecast_parsed"):
                self._append_solcast_memory_snapshot()
                if await self._ensure_solcast_store():
                    try:
                        from copy import deepcopy

                        from .solcast_forecast_metrics import strip_volatile_forecast_metrics

                        poll_cache = deepcopy(self._solcast_cache)
                        parsed = poll_cache.get("pv_forecast_parsed")
                        if isinstance(parsed, dict):
                            poll_cache["pv_forecast_parsed"] = strip_volatile_forecast_metrics(
                                parsed
                            )
                        async with self._solcast_store_lock:
                            self._solcast_history_count = (
                                await self._solcast_store.async_record_poll(poll_cache)
                            )
                            synth = self._stored_from_memory_snapshots()
                            if synth:
                                self._remember_solcast_stored(synth)
                        await self._safe_archive_solcast_daily_forecasts()
                        _LOGGER.debug(
                            "Persisted Solcast forecast to storage (%s periods)",
                            (self._solcast_cache.get("pv_forecast_parsed") or {}).get(
                                "period_count"
                            ),
                        )
                    except Exception:
                        synth = self._stored_from_memory_snapshots()
                        if synth:
                            self._remember_solcast_stored(synth)
                        _LOGGER.warning(
                            "Solcast forecast persist failed after poll; kept in-memory cache"
                        )
                try:
                    await self._rebuild_solcast_forecast_chart()
                except Exception:
                    _LOGGER.exception("Solcast forecast chart rebuild failed after poll")
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
                category_ids=cfg.storm_weather_categories,
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
            await self._clear_smart_charge_export_before_higher_priority()
            await self._arm_policy(
                MODE_OUTAGE,
                self.plant.outage_prep.charge_periods,
                reason,
                self.plant.outage_prep.target_max_soc,
                EVENT_OUTAGE_ARMED,
            )
            return

        if self.plant.storm_prep.enabled and self._active_storm_triggers:
            solcast_decision = self._storm_solcast_arm_decision()
            periods = solcast_decision["periods"]
            reason = (
                f"storm:{','.join(sorted(self._active_storm_triggers))}"
                f"|solcast:{solcast_decision['action']}"
            )
            if self.plant.override.active and self.plant.override.mode == MODE_STORM:
                if self.plant.override.reason == reason:
                    return
            await self._clear_smart_charge_export_before_higher_priority()
            await self._arm_policy(
                MODE_STORM,
                periods,
                reason,
                self.plant.storm_prep.target_max_soc,
                EVENT_STORM_ARMED,
            )
            return

        if self._smart_charge_armed or self._smart_charge_discharge_armed:
            return

        if self._forecast_armed:
            return

        if self.plant.override.active and self.plant.override.mode in AUTOMATION_MODES:
            mode = self.plant.override.mode
            event = {
                MODE_STORM: EVENT_STORM_DISARMED,
                MODE_OUTAGE: EVENT_OUTAGE_DISARMED,
                MODE_FORECAST: EVENT_FORECAST_DISARMED,
                MODE_SMART_CHARGE: EVENT_SMART_CHARGE_DISARMED,
            }.get(mode)
            if event:
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
        self._save_work_mode_if_needed()
        await self.async_set_override_periods(periods, mode, reason)
        if target_max_soc is not None:
            await self._set_max_soc(target_max_soc)
        self._fire(event_name, {"reason": reason, "mode": mode})

    async def _disarm_policy(self, mode: str, event_name: str) -> None:
        if not (self.plant.override.active and self.plant.override.mode == mode):
            return
        saved_max_soc = self.plant.override.saved_max_soc
        saved_work_mode = self.plant.override.saved_work_mode
        self.plant.override = OverrideState()
        await self._persist()
        await self._restore_after_automation_disarm(
            saved_max_soc=saved_max_soc,
            saved_work_mode=saved_work_mode,
        )
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
        if self._smart_charge_armed:
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

    def _live_home_load_kw(self) -> float | None:
        load_w = self._entity_float("load_power")
        if load_w is None:
            return None
        return max(0.0, abs(load_w) / 1000.0)

    def _smart_charge_rate_slots(self, *, horizon_hours: int) -> list:
        from .octopus_tariff import is_tracker_tariff_type
        from .smart_charge import rate_slots_from_octopus, rate_slots_from_schedule
        from .smart_charge.grid_charge import merge_rate_slots_to_hours

        if self._octopus_agile_active():
            slots = rate_slots_from_octopus(
                self._octopus_cache.get("import_rates") or [],
                self._octopus_cache.get("export_rates") or [],
                horizon_hours=horizon_hours,
            )
        elif self._octopus_entity_active():
            import_rows, export_rows = self._smart_charge_entity_rate_rows()
            if import_rows:
                slots = rate_slots_from_octopus(
                    import_rows,
                    export_rows or None,
                    horizon_hours=horizon_hours,
                )
            else:
                slots = rate_slots_from_schedule(self.plant.tariff, horizon_hours=horizon_hours)
        elif self._octopus_cache.get("import_rates"):
            slots = rate_slots_from_octopus(
                self._octopus_cache.get("import_rates") or [],
                self._octopus_cache.get("export_rates") or [],
                horizon_hours=horizon_hours,
            )
        else:
            slots = rate_slots_from_schedule(self.plant.tariff, horizon_hours=horizon_hours)

        if is_tracker_tariff_type(self._smart_charge_tariff_type()):
            slots = merge_rate_slots_to_hours(slots)
        return slots

    def _smart_charge_greener_inputs(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        cache = self._octopus_greener_cache or {}
        carbon = cache.get("carbon_periods") if isinstance(cache.get("carbon_periods"), list) else []
        greener = cache.get("greener_nights") if isinstance(cache.get("greener_nights"), list) else []
        return carbon, greener

    async def _clear_smart_charge_export_before_higher_priority(self) -> None:
        if self._smart_charge_discharge_armed:
            await self._disarm_smart_charge_export()
        self._smart_charge_armed = False
        self._smart_charge_discharge_armed = False
        self._smart_charge_periods_sig = ""
        self._smart_charge_discharge_sig = ""

    async def _enable_force_discharge(self) -> None:
        entity_id = self.plant.entity_map.get("work_mode")
        options = self._entity_options("work_mode")
        if entity_id and options and "Force Discharge" in options:
            await self._set_work_mode("Force Discharge")
            return
        await set_remote_control_mode(self.hass, self.plant.entity_map, "Force Discharge")

    async def _disarm_smart_charge_export(self) -> None:
        if not self._smart_charge_discharge_armed:
            return
        self._smart_charge_discharge_armed = False
        self._smart_charge_discharge_sig = ""
        saved_max_soc = self.plant.override.saved_max_soc
        saved_work_mode = self.plant.override.saved_work_mode
        if (
            self.plant.override.active
            and self.plant.override.mode == MODE_SMART_CHARGE
            and (self.plant.override.reason or "").startswith("smart_charge:export")
        ):
            self.plant.override = OverrideState()
            await self._persist()
            await self._restore_after_automation_disarm(
                saved_max_soc=saved_max_soc,
                saved_work_mode=saved_work_mode,
            )
        else:
            await self._clear_remote_control_for_restore()
        self._fire(EVENT_SMART_CHARGE_DISARMED, {"reason": "export_complete"})

    async def _arm_smart_charge_export(self, decision: Any) -> None:
        from .smart_charge import discharge_window_signature

        window = decision.discharge_window or (decision.windows[0] if decision.windows else None)
        sig = discharge_window_signature(window)
        if self._smart_charge_armed:
            self._smart_charge_armed = False
            self._smart_charge_periods_sig = ""
            if self.plant.override.active and self.plant.override.mode == MODE_SMART_CHARGE:
                reason = self.plant.override.reason or ""
                if reason.startswith("smart_charge:") and "export" not in reason:
                    await self._disarm_policy(MODE_SMART_CHARGE, EVENT_SMART_CHARGE_DISARMED)

        if self.plant.override.active and self.plant.override.mode not in AUTOMATION_MODES:
            return

        if not self._smart_charge_discharge_armed:
            self._smart_charge_discharge_armed = True
            self._smart_charge_discharge_sig = sig
            await self._save_work_mode_if_needed()
            self.plant.override.active = True
            self.plant.override.mode = MODE_SMART_CHARGE
            self.plant.override.reason = "smart_charge:export_discharge"
            self.plant.override.periods = [
                ChargePeriodConfig.from_dict(p.to_dict()) for p in self.plant.baseline_periods
            ]
            await self._persist()
            await self._enable_force_discharge()
            self._fire(
                EVENT_SMART_CHARGE_ARMED,
                {"reason": "smart_charge:export_discharge", "mode": MODE_SMART_CHARGE},
            )
            return

        if sig != self._smart_charge_discharge_sig:
            self._smart_charge_discharge_sig = sig
            await self._enable_force_discharge()
            self._fire(
                EVENT_SMART_CHARGE_ARMED,
                {"reason": "smart_charge:export_discharge", "mode": MODE_SMART_CHARGE},
            )

    async def _arm_smart_charge_grid(self, decision: Any) -> None:
        from .smart_charge import charge_periods_signature

        if self._smart_charge_discharge_armed:
            await self._disarm_smart_charge_export()

        should_arm = decision.action in ("grid_charge", "arbitrage", "spread_plan") and decision.charge_periods
        new_sig = charge_periods_signature(decision.charge_periods) if decision.charge_periods else ""
        if should_arm and not self._smart_charge_armed:
            self._smart_charge_armed = True
            self._smart_charge_periods_sig = new_sig
            if self.plant.override.active and self.plant.override.mode not in AUTOMATION_MODES:
                return
            await self._arm_policy(
                MODE_SMART_CHARGE,
                decision.charge_periods,
                f"smart_charge:{decision.action}",
                decision.target_max_soc,
                EVENT_SMART_CHARGE_ARMED,
            )
        elif not should_arm and self._smart_charge_armed:
            self._smart_charge_armed = False
            self._smart_charge_periods_sig = ""
            if self.plant.override.active and self.plant.override.mode == MODE_SMART_CHARGE:
                await self._disarm_policy(MODE_SMART_CHARGE, EVENT_SMART_CHARGE_DISARMED)
        elif should_arm and self._smart_charge_armed:
            if self.plant.override.active and self.plant.override.mode == MODE_SMART_CHARGE:
                if (
                    new_sig != self._smart_charge_periods_sig
                    or self.plant.override.reason != f"smart_charge:{decision.action}"
                ):
                    self._smart_charge_periods_sig = new_sig
                    await self._arm_policy(
                        MODE_SMART_CHARGE,
                        decision.charge_periods,
                        f"smart_charge:{decision.action}",
                        decision.target_max_soc,
                        EVENT_SMART_CHARGE_ARMED,
                    )

    async def _evaluate_smart_charge_daily_plan(self) -> None:
        from .smart_charge import build_daily_plan

        cfg = self.plant.smart_charge
        if not cfg.enabled or not self.plant.control_active:
            return
        if self.plant.outage_prep.enabled and self._active_outage_triggers:
            return
        if self.plant.storm_prep.enabled and self._active_storm_triggers:
            return

        if self._octopus_native_active():
            await self._async_refresh_octopus(force=True)

        tariff_type = self._smart_charge_tariff_type()

        forecast_rows = self._solcast_detailed_forecast_rows()
        if not forecast_rows and self._solcast_cache.get("detailed_forecast"):
            raw = self._solcast_cache.get("detailed_forecast")
            forecast_rows = raw if isinstance(raw, list) else []

        horizon = max(1, int(cfg.daily_plan_horizon_hours or 24))
        import_slots = self._smart_charge_rate_slots(horizon_hours=horizon)
        soc_pct = self._entity_float("battery_soc")
        capacity_kwh = self._entity_float("bms_kwh_nominal")
        kwh_remaining = self._entity_float("battery_kwh_remaining")
        if capacity_kwh is None or capacity_kwh <= 0:
            if soc_pct and soc_pct > 0 and kwh_remaining is not None:
                capacity_kwh = kwh_remaining * 100.0 / soc_pct
        carbon_periods, greener_nights = self._smart_charge_greener_inputs()
        self._smart_charge_daily_plan = build_daily_plan(
            config=cfg,
            import_slots=import_slots,
            forecast_rows=forecast_rows,
            live_load_kw=self._live_home_load_kw(),
            horizon_hours=float(horizon),
            exportable_kwh=None,
            capacity_kwh=capacity_kwh,
            kwh_remaining=kwh_remaining,
            soc_pct=soc_pct,
            carbon_periods=carbon_periods,
            greener_nights=greener_nights,
            tariff_type=tariff_type,
        )
        await self._evaluate_smart_charge()

    async def _evaluate_smart_charge(self) -> None:
        from .smart_charge import current_plan_slot, evaluate_smart_charge

        cfg = self.plant.smart_charge
        if not cfg.enabled or not self.plant.control_active:
            return
        if self.plant.outage_prep.enabled and self._active_outage_triggers:
            await self._disarm_smart_charge_export()
            return
        if self.plant.storm_prep.enabled and self._active_storm_triggers:
            await self._disarm_smart_charge_export()
            return

        forecast_rows = self._solcast_detailed_forecast_rows()
        if not forecast_rows and self._solcast_cache.get("detailed_forecast"):
            raw = self._solcast_cache.get("detailed_forecast")
            forecast_rows = raw if isinstance(raw, list) else []

        horizon = max(1, int(cfg.daily_plan_horizon_hours or 24))
        import_slots = self._smart_charge_rate_slots(horizon_hours=horizon)
        export_slots = import_slots
        tariff_type = self._smart_charge_tariff_type()

        soc_pct = self._entity_float("battery_soc")
        capacity_kwh = self._entity_float("bms_kwh_nominal")
        kwh_remaining = self._entity_float("battery_kwh_remaining")
        if capacity_kwh is None or capacity_kwh <= 0:
            cap_from_soc = None
            if soc_pct and soc_pct > 0 and kwh_remaining is not None:
                cap_from_soc = kwh_remaining * 100.0 / soc_pct
            capacity_kwh = cap_from_soc

        decision = evaluate_smart_charge(
            config=cfg,
            soc_pct=soc_pct,
            capacity_kwh=capacity_kwh,
            kwh_remaining=kwh_remaining,
            forecast_rows=forecast_rows,
            import_slots=import_slots,
            export_slots=export_slots,
            live_load_kw=self._live_home_load_kw(),
            daily_plan=self._smart_charge_daily_plan,
            horizon_hours=float(horizon),
            tariff_type=tariff_type,
        )
        self._smart_charge_decision = decision.to_dict()
        self._smart_charge_decision["current_plan_slot"] = current_plan_slot(self._smart_charge_daily_plan)

        if decision.action == "export_discharge":
            await self._arm_smart_charge_export(decision)
        elif decision.action in ("grid_charge", "arbitrage", "spread_plan"):
            await self._arm_smart_charge_grid(decision)
        else:
            if self._smart_charge_discharge_armed:
                await self._disarm_smart_charge_export()
            if self._smart_charge_armed:
                self._smart_charge_armed = False
                self._smart_charge_periods_sig = ""
                if self.plant.override.active and self.plant.override.mode == MODE_SMART_CHARGE:
                    await self._disarm_policy(MODE_SMART_CHARGE, EVENT_SMART_CHARGE_DISARMED)

    async def _save_max_soc_if_needed(self, target: float | None) -> None:
        if target is None or self.plant.override.saved_max_soc is not None:
            return
        current = self._entity_state("max_soc")
        if current not in (None, "unknown", "unavailable"):
            try:
                self.plant.override.saved_max_soc = float(current)
            except ValueError:
                pass

    def _save_work_mode_if_needed(self) -> None:
        if self.plant.override.saved_work_mode is not None:
            return
        current = self._entity_state("work_mode")
        if current and current not in TRANSIENT_WORK_MODE_OPTIONS:
            self.plant.override.saved_work_mode = current

    async def _clear_remote_control_for_restore(self) -> None:
        current = self._entity_state("work_mode")
        if current not in ("Force Charge", "Force Discharge"):
            return
        if not self.plant.entity_map.get("remote_control"):
            return
        try:
            await set_remote_control_mode(self.hass, self.plant.entity_map, "Disable")
        except HomeAssistantError as err:
            _LOGGER.debug("Remote Control disable before restore skipped: %s", err)

    async def _set_work_mode(self, option: str) -> None:
        entity_id = self.plant.entity_map.get("work_mode")
        if not entity_id:
            return
        options = self._entity_options("work_mode")
        if options and option not in options:
            _LOGGER.warning(
                "Cannot restore work mode %r; not in entity options (%s)",
                option,
                ", ".join(options),
            )
            return
        await self.hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": option},
            blocking=True,
        )
        _LOGGER.info("Restored work mode to %s on %s", option, entity_id)

    async def _restore_after_automation_disarm(
        self,
        *,
        saved_max_soc: float | None,
        saved_work_mode: str | None,
    ) -> None:
        await self._clear_remote_control_for_restore()
        await self.async_apply_desired()
        if saved_max_soc is not None:
            await self._set_max_soc(saved_max_soc)
        if saved_work_mode:
            await self._set_work_mode(saved_work_mode)

    async def _set_max_soc(self, value: float) -> None:
        current = {
            "min_soc": self._entity_float("min_soc"),
            "min_soc_on_grid": self._entity_float("min_soc_on_grid"),
            "max_soc": self._entity_float("max_soc"),
        }
        min_soc = int(current.get("min_soc") or 10)
        min_soc_on_grid = int(current.get("min_soc_on_grid") or 10)
        max_soc = int(round(value))
        target = clamp_soc_values(min_soc, min_soc_on_grid, max_soc)
        await apply_soc_limits(
            self.hass,
            self.plant.entity_map,
            min_soc=target["min_soc"],
            min_soc_on_grid=target["min_soc_on_grid"],
            max_soc=target["max_soc"],
            current=current,
            force_write=True,
            inverter_target=self.plant.inverter_target,
            device_id=self.plant.device_id,
            live_battery_soc=self._entity_float("battery_soc"),
        )

    async def async_set_soc_limits(
        self,
        min_soc: int,
        min_soc_on_grid: int,
        max_soc: int,
    ) -> list[dict[str, Any]]:
        """Write all three SOC limits in an inverter-safe order."""
        return await apply_soc_limits(
            self.hass,
            self.plant.entity_map,
            min_soc=min_soc,
            min_soc_on_grid=min_soc_on_grid,
            max_soc=max_soc,
            force_write=True,
            verify=True,
            inverter_target=self.plant.inverter_target,
            device_id=self.plant.device_id,
            live_battery_soc=self._entity_float("battery_soc"),
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
            category_ids=self.plant.storm_prep.storm_weather_categories,
        )
        out["condition_active"] = self._is_storm_condition_active()
        out["forecast_active"] = self._storm_forecast_active
        out["forecast_detail"] = self._storm_forecast_detail
        out["solcast_precheck"] = self._storm_solcast_precheck()
        return out

    def _storm_solcast_precheck(self) -> dict[str, Any]:
        from .storm_solcast import evaluate_storm_solcast_precheck

        cfg = self.plant.storm_prep
        return evaluate_storm_solcast_precheck(
            cfg=cfg,
            solcast_configured=bool(
                self.plant.solcast.enabled
                and self.plant.solcast.api_key_configured()
                and self._solcast_detailed_forecast_rows()
            ),
            forecast_rows=self._solcast_detailed_forecast_rows(),
            condition_active=self._is_storm_condition_active(),
            forecast_active=self._storm_forecast_active,
            forecast_detail=self._storm_forecast_detail,
            soc_pct=self._entity_float("battery_soc"),
            capacity_kwh=self._entity_float("bms_kwh_nominal"),
            kwh_remaining=self._entity_float("battery_kwh_remaining"),
        )

    def _storm_solcast_arm_decision(self) -> dict[str, Any]:
        decision = self._storm_solcast_precheck()
        periods = decision.get("periods")
        if not isinstance(periods, list) or not periods:
            periods = self.plant.storm_prep.charge_periods
        return {
            "action": decision.get("action"),
            "periods": periods,
        }

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
            "smart_charge_armed": self._smart_charge_armed,
            "smart_charge": {
                **self.plant.smart_charge.to_dict(),
                "armed": self._smart_charge_armed,
                "discharge_armed": self._smart_charge_discharge_armed,
                "decision": self._smart_charge_decision,
                "daily_plan": self._smart_charge_daily_plan,
            },
            "tariff_modes": sorted(self.plant.tariff_modes.keys()),
            "storm_prep": self._storm_prep_state(),
            "overview_weather": self._overview_weather_state(),
            "outage_prep": self.plant.outage_prep.to_dict(),
            "panel_display": self.plant.panel_display.to_dict(),
            "pv_config": self.plant.pv_config.to_dict(),
            "solcast": self._solcast_state(),
            "glow": self._glow_state(),
            "tariff": self._tariff_state(),
            "panel_runtime": get_panel_disk_info(self.hass),
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
        from .glow_grid import apply_glow_grid_overlay

        states = {key: self._entity_state(key) for key in ANALYTICS_ENTITY_SUFFIXES}
        if not any(states.values()):
            analytics: dict[str, Any] = {}
        else:
            analytics = compute_analytics(states)
        return apply_glow_grid_overlay(
            analytics,
            self._glow_live,
            enabled=self._glow_enabled(),
        )

    def _glow_enabled(self) -> bool:
        return bool(self.plant.glow.enabled)

    def _glow_state(self) -> dict[str, Any]:
        from .glow_grid import glow_status_dict

        return glow_status_dict(self.plant.glow, self._glow_live)

    def register_glow_sensor(self, kind: str, sensor: Any) -> None:
        self._glow_sensors[kind] = sensor

    async def async_update_glow_sensors(self) -> None:
        if not self._glow_enabled():
            return
        live = self._glow_live
        values = {
            "import_power": live.get("import_kw"),
            "import_today": live.get("import_kwh_today"),
            "import_cumulative": live.get("import_kwh_cumulative"),
        }
        for kind, value in values.items():
            sensor = self._glow_sensors.get(kind)
            if sensor is None:
                continue
            sensor.set_value(float(value) if value is not None else None)
            await sensor.async_publish()

    @callback
    def _on_glow_mqtt_electricity(self, payload: dict[str, Any], device_mac: str) -> None:
        from homeassistant.util import dt as dt_util

        self._glow_live = {**payload, "device_mac": device_mac}
        glow = self.plant.glow
        glow.last_mqtt_at = payload.get("timestamp") or dt_util.utcnow().isoformat()
        glow.mqtt_connected = True
        glow.device_mac = device_mac
        glow.last_error = None
        self.hass.async_create_task(self._async_glow_live_updated())

    async def _async_glow_live_updated(self) -> None:
        await self.async_update_glow_sensors()
        await self.async_request_refresh()

    def _teardown_glow_mqtt(self) -> None:
        if self._glow_unsub_mqtt:
            self._glow_unsub_mqtt()
            self._glow_unsub_mqtt = None
        self.plant.glow.mqtt_connected = False

    def _setup_glow_mqtt(self) -> None:
        self._teardown_glow_mqtt()
        glow = self.plant.glow
        if not glow.enabled or not glow.mqtt_enabled:
            return
        from .glow_mqtt import async_subscribe_glow_mqtt, mqtt_broker_configured

        if not mqtt_broker_configured(self.hass):
            glow.last_error = "MQTT broker not configured in Home Assistant"
            return

        async def _subscribe() -> None:
            try:
                self._glow_unsub_mqtt = await async_subscribe_glow_mqtt(
                    self.hass,
                    topic_prefix=glow.topic_prefix,
                    device_id=glow.device_id,
                    on_electricity=self._on_glow_mqtt_electricity,
                )
                glow.last_error = None
            except Exception as err:
                glow.last_error = str(err)
                _LOGGER.warning("Glow MQTT subscribe failed: %s", err)

        self.hass.async_create_task(_subscribe())

    async def _async_refresh_glow_api(self, *, force_auth: bool = False) -> None:
        glow = self.plant.glow
        if not glow.enabled or not glow.api_enabled:
            return
        from homeassistant.util import dt as dt_util

        from .glow_api import GlowApiClient, GlowApiError, classify_glow_resources
        from .glow_grid import parse_glow_electricity_payload

        token = glow.token
        if force_auth or not glow.token_configured():
            if not glow.credentials_configured():
                glow.last_error = "Bright username and password required for Glow API"
                return
            auth = await GlowApiClient.authenticate(
                self.hass,
                username=str(glow.username),
                password=str(glow.password),
            )
            token = str(auth.get("token"))
            glow.token = token
            try:
                glow.token_exp = int(auth.get("exp")) if auth.get("exp") is not None else None
            except (TypeError, ValueError):
                glow.token_exp = None

        client = GlowApiClient(self.hass, token=token)
        try:
            resources = await client.list_resources()
            import_id, export_id = classify_glow_resources(resources)
            if import_id:
                glow.import_resource_id = import_id
            if export_id:
                glow.export_resource_id = export_id
            if glow.import_resource_id:
                current = await client.get_current(glow.import_resource_id)
                parsed = parse_glow_electricity_payload(current, source="glow_api")
                if parsed:
                    self._glow_live = {**self._glow_live, **parsed}
            glow.last_api_at = dt_util.utcnow().isoformat()
            glow.last_error = None
        except GlowApiError as err:
            glow.last_error = str(err)
            _LOGGER.warning("Glow API refresh failed: %s", err)

    async def async_save_glow(self, *, glow: dict[str, Any], fetch_now: bool = True) -> None:
        from .models import merge_glow_config

        fetch_now = bool(glow.pop("fetch_now", fetch_now))
        current = self.plant.glow.to_dict()
        merged = merge_glow_config(current, glow)
        cfg = GlowConfig.from_dict(merged)
        if cfg.enabled and cfg.api_enabled and not cfg.mqtt_enabled and not cfg.credentials_configured():
            raise HomeAssistantError("Bright username and password required when MQTT is disabled")
        data = dict(self.config_entry.data)
        data[CONF_GLOW] = cfg.to_dict()
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        self._setup_glow_mqtt()
        if fetch_now and cfg.enabled and cfg.api_enabled:
            await self._async_refresh_glow_api(force_auth=True)
            await self.async_update_glow_sensors()
        await self.async_request_refresh()

    async def async_test_glow(self, *, username: str | None = None, password: str | None = None) -> dict[str, Any]:
        from .glow_api import GlowApiClient, GlowApiError, classify_glow_resources
        from .models import merge_glow_config

        glow = self.plant.glow
        user = (username or glow.username or "").strip()
        pw = password or glow.password or ""
        if not user or not pw:
            raise HomeAssistantError("Bright username and password required")
        auth = await GlowApiClient.authenticate(self.hass, username=user, password=pw)
        token = str(auth.get("token") or "")
        client = GlowApiClient(self.hass, token=token)
        resources = await client.list_resources()
        import_id, export_id = classify_glow_resources(resources)
        merged = merge_glow_config(
            self.plant.glow.to_dict(),
            {
                "username": user,
                "password": pw,
                "token": token,
                "token_exp": auth.get("exp"),
                **({"import_resource_id": import_id} if import_id else {}),
                **({"export_resource_id": export_id} if export_id else {}),
            },
        )
        cfg = GlowConfig.from_dict(merged)
        data = dict(self.config_entry.data)
        data[CONF_GLOW] = cfg.to_dict()
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        return {
            "valid": bool(auth.get("valid")),
            "account_id": auth.get("accountId"),
            "resource_count": len(resources),
            "import_resource_id": import_id,
            "export_resource_id": export_id,
            "resources": [
                {
                    "id": row.get("id") or row.get("resourceId"),
                    "name": row.get("name") or row.get("label"),
                    "type": row.get("resourceType") or row.get("type"),
                }
                for row in resources[:12]
                if isinstance(row, dict)
            ],
        }


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
        self._enrich_solcast_cache_metrics()
        try:
            await self._evaluate_smart_charge()
        except Exception as err:
            _LOGGER.warning("Smart charge evaluation failed: %s", err)
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
        saved_max_soc = self.plant.override.saved_max_soc
        saved_work_mode = self.plant.override.saved_work_mode
        self.plant.override = OverrideState()
        self._forecast_armed = False
        await self._persist()
        await self._restore_after_automation_disarm(
            saved_max_soc=saved_max_soc,
            saved_work_mode=saved_work_mode,
        )
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
        saved_max_soc = self.plant.override.saved_max_soc
        saved_work_mode = self.plant.override.saved_work_mode
        self.plant.override = OverrideState()
        self._forecast_armed = False
        self._smart_charge_armed = False
        self._smart_charge_discharge_armed = False
        self._active_storm_triggers.clear()
        self._active_outage_triggers.clear()
        await self._persist()
        await self._restore_after_automation_disarm(
            saved_max_soc=saved_max_soc,
            saved_work_mode=saved_work_mode,
        )
        if mode == MODE_STORM:
            self._fire(EVENT_STORM_DISARMED, {})
        elif mode == MODE_OUTAGE:
            self._fire(EVENT_OUTAGE_DISARMED, {})
        elif mode == MODE_FORECAST:
            self._fire(EVENT_FORECAST_DISARMED, {})
        elif mode == MODE_SMART_CHARGE:
            self._fire(EVENT_SMART_CHARGE_DISARMED, {})
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
        use_solcast_grid_limit: bool | None = None,
        solcast_safety_margin: float | None = None,
        solcast_min_soc_floor: float | None = None,
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
            "use_solcast_grid_limit": (
                bool(use_solcast_grid_limit)
                if use_solcast_grid_limit is not None
                else self.plant.storm_prep.use_solcast_grid_limit
            ),
            "solcast_safety_margin": (
                float(solcast_safety_margin)
                if solcast_safety_margin is not None
                else self.plant.storm_prep.solcast_safety_margin
            ),
            "solcast_min_soc_floor": (
                float(solcast_min_soc_floor)
                if solcast_min_soc_floor is not None
                else self.plant.storm_prep.solcast_min_soc_floor
            ),
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
        await self._sync_automation_policy()
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
        cfg = PvSystemConfig.from_dict(pv_config)
        if self.plant.solcast.installation_date:
            from .pv_efficiency import sync_pv_efficiency_from_install

            cfg, _changed = sync_pv_efficiency_from_install(
                cfg, self.plant.solcast.installation_date
            )
        data = dict(self.config_entry.data)
        data[CONF_PV_CONFIG] = cfg.to_dict()
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        if self._solcast_pv_active():
            await self._async_refresh_solcast_pv(force=True)
        await self.async_request_refresh()

    async def async_save_tariff(self, *, tariff: dict[str, Any]) -> None:
        """Persist electricity tariff rates from the panel."""
        from homeassistant.util import dt as dt_util

        from .models import merge_tariff_dynamic_config
        from .tariff_rates import TARIFF_SOURCE_ENTITY, resolve_tariff_rates
        from .tariff_store import TariffRateStore

        tariff_payload = dict(tariff)
        incoming_dynamic = tariff_payload.get("dynamic")
        if isinstance(incoming_dynamic, dict):
            current_dynamic = self.plant.tariff.dynamic.to_dict(include_api_key=True)
            tariff_payload["dynamic"] = merge_tariff_dynamic_config(
                current_dynamic, incoming_dynamic
            )
        cfg = TariffConfig.from_dict(tariff_payload)
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
        self._setup_octopus_greener_timer()
        self._setup_octopus_consumption_timer()
        await self.async_request_refresh()

    async def async_save_octopus(
        self,
        *,
        dynamic: dict[str, Any],
        fetch_now: bool = True,
        apply_schedule: bool = False,
    ) -> None:
        """Persist Octopus dynamic tariff settings from the panel."""
        from .models import TariffDynamicConfig, merge_tariff_dynamic_config
        from .octopus_tariff import OCTOPUS_PROVIDER, OCTOPUS_SOURCE_ENTITY, OCTOPUS_SOURCE_NATIVE
        from .tariff_rates import TARIFF_SOURCE_ENTITY

        fetch_now = bool(dynamic.pop("fetch_now", fetch_now))
        apply_schedule = bool(dynamic.pop("apply_schedule", apply_schedule))
        current = self.plant.tariff.dynamic.to_dict(include_api_key=True)
        merged = merge_tariff_dynamic_config(current, dynamic)
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
            await self._async_refresh_octopus(force=True)
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
        elif fetch_now and self._octopus_greener_enabled():
            await self._async_refresh_octopus_greener(force=True)
        self._setup_tariff_schedule_timer()
        self._setup_octopus_timer()
        self._setup_octopus_greener_timer()
        self._setup_octopus_consumption_timer()
        self._setup_smart_charge_entity_listener()
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
        self._setup_octopus_greener_timer()
        self._setup_octopus_consumption_timer()
        await self.async_request_refresh()
        return self._octopus_status()

    async def _async_auto_apply_octopus_schedule(self) -> None:
        """Push a fetched fixed-tariff Octopus schedule into tariff config."""
        from .octopus_tariff import is_variable_tariff_type

        if not self.plant.tariff.dynamic.native_octopus():
            return
        if self._octopus_cache.get("last_error"):
            return
        schedule_raw = self._octopus_cache.get("schedule")
        if not schedule_raw:
            return
        tariff_type = str(self._octopus_cache.get("tariff_type") or "")
        if is_variable_tariff_type(tariff_type):
            return
        try:
            await self.async_apply_octopus_schedule()
        except HomeAssistantError as err:
            _LOGGER.debug("Octopus schedule auto-apply skipped: %s", err)

    async def async_apply_octopus_schedule(self) -> dict[str, Any]:
        """Apply the last fetched fixed-tariff schedule to tariff config."""
        from .const import TARIFF_KIND_STATIC
        from .octopus_tariff import is_variable_tariff_type
        from .tariff_rates import TARIFF_SOURCE_SCHEDULE
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
        if cfg.dynamic.native_octopus():
            cfg.import_source = TARIFF_SOURCE_SCHEDULE
            cfg.export_source = TARIFF_SOURCE_SCHEDULE
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

    async def async_save_smart_charge(self, *, smart_charge: dict[str, Any]) -> None:
        """Persist smart charge settings from the panel."""
        from .const import DEFAULT_SMART_CHARGE
        from .models import SmartChargeConfig

        merged = {**self.plant.smart_charge.to_dict(), **smart_charge}
        periods_raw = merged.get("charge_periods") or DEFAULT_SMART_CHARGE["charge_periods"]
        cfg = SmartChargeConfig.from_dict(merged, periods_raw)
        data = dict(self.config_entry.data)
        data[CONF_SMART_CHARGE] = cfg.to_dict()
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        self._setup_smart_charge_timer()
        self._setup_smart_charge_daily_plan_timer()
        self._setup_smart_charge_entity_listener()
        try:
            await self._evaluate_smart_charge()
        except Exception as err:
            _LOGGER.warning("Smart charge evaluation failed after save: %s", err)
        await self.async_request_refresh()

    async def _async_refresh_octopus(self, *, force: bool = False) -> None:
        from .octopus_api import OctopusApiClient, OctopusApiError
        from .octopus_tariff import fetch_octopus_tariff_snapshot, list_account_meters

        dyn = self.plant.tariff.dynamic
        if not dyn.native_octopus():
            return
        if not dyn.api_key_configured() or not dyn.account_number:
            self._octopus_cache["last_error"] = "Octopus API key and account number required"
            return
        if not force and not self._octopus_tariff_refresh_due():
            _LOGGER.debug("Octopus tariff refresh skipped (cache fresh)")
            return
        if not force and self._octopus_rate_limited():
            _LOGGER.debug("Octopus tariff refresh skipped (rate limited)")
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
            self._octopus_cache["import_rates"] = snapshot.import_rates
            self._octopus_cache["export_rates"] = snapshot.export_rates
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
            await self._async_auto_apply_octopus_schedule()
        except OctopusApiError as err:
            self._note_octopus_rate_limit(str(err))
            self._octopus_cache["last_error"] = str(err)
            _LOGGER.warning("Octopus tariff fetch failed: %s", err)

    async def _async_refresh_octopus_greener(self, *, force: bool = False) -> None:
        if not self._octopus_greener_enabled():
            return
        if not force and not self._octopus_greener_refresh_due():
            _LOGGER.debug("Octopus greener refresh skipped (cache fresh)")
            if not self._octopus_analysis_cache:
                await self._async_refresh_octopus_analysis()
            return
        if not force and self._octopus_rate_limited():
            _LOGGER.debug("Octopus greener refresh skipped (rate limited)")
            if not self._octopus_analysis_cache:
                await self._async_refresh_octopus_analysis()
            return
        from homeassistant.util import dt as dt_util

        from .octopus_greener import (
            fetch_octopus_greener_snapshot,
            merge_octopus_greener_snapshots,
        )
        from .octopus_greener_store import OctopusGreenerStore

        dyn = self.plant.tariff.dynamic
        api_key = str(dyn.api_key) if dyn.api_key_configured() else None
        account_number = str(dyn.account_number) if dyn.account_number else None
        previous = dict(self._octopus_greener_cache or {})
        try:
            incoming = await fetch_octopus_greener_snapshot(
                self.hass,
                api_key=api_key,
                account_number=account_number,
            )
            self._note_octopus_rate_limit(*(incoming.get("errors") or {}).values())
            from .octopus_greener import hydrate_greener_snapshot_from_history

            merged = merge_octopus_greener_snapshots(previous, incoming)
            merged = hydrate_greener_snapshot_from_history(merged, self._octopus_greener_history)
            self._octopus_greener_cache = merged
            if merged.get("carbon_periods") or merged.get("greener_nights"):
                if self._octopus_greener_store is None:
                    self._octopus_greener_store = OctopusGreenerStore(
                        self.hass, self.config_entry.entry_id
                    )
                self._octopus_greener_history_count = await self._octopus_greener_store.async_record_snapshot(
                    snapshot=merged,
                    recorded_at=dt_util.utcnow().isoformat(),
                )
                stored = await self._octopus_greener_store.async_load()
                self._octopus_greener_history = OctopusGreenerStore.history_entries(stored)
            await self._async_refresh_octopus_analysis()
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.warning("Octopus greener refresh failed: %s", err)
            self._note_octopus_rate_limit(str(err))
            if previous:
                errors = dict(previous.get("errors") or {})
                errors["_refresh"] = str(err)
                previous["errors"] = errors
                self._octopus_greener_cache = previous
            await self._async_refresh_octopus_analysis()
            await self.async_request_refresh()

    async def _async_refresh_octopus_analysis(self) -> None:
        if not self._octopus_greener_enabled():
            return
        from .octopus_analysis import build_octopus_analysis_snapshot

        dyn = self.plant.tariff.dynamic
        api_key = str(dyn.api_key) if dyn.api_key_configured() else None
        try:
            self._octopus_analysis_cache = await build_octopus_analysis_snapshot(
                self.hass,
                api_key=api_key,
                octopus_cache=self._octopus_cache,
                greener_cache=self._octopus_greener_cache,
                greener_history=self._octopus_greener_history,
                consumption_data=self._octopus_consumption_data,
            )
        except Exception as err:
            _LOGGER.warning("Octopus analysis refresh failed: %s", err)

    async def _async_refresh_octopus_consumption(self, *, force: bool = False) -> None:
        if not self._octopus_greener_enabled():
            return
        dyn = self.plant.tariff.dynamic
        if not dyn.api_key_configured():
            return
        if not force and not self._octopus_consumption_refresh_due():
            _LOGGER.debug("Octopus consumption refresh skipped (cache fresh)")
            return
        if not force and self._octopus_rate_limited():
            _LOGGER.debug("Octopus consumption refresh skipped (rate limited)")
            return
        from .octopus_analysis import refresh_octopus_consumption
        from .octopus_consumption_store import OctopusConsumptionStore

        if self._octopus_consumption_store is None:
            self._octopus_consumption_store = OctopusConsumptionStore(
                self.hass, self.config_entry.entry_id
            )
        api_key = str(dyn.api_key)
        try:
            # First poll after install: backfill ~35 days; thereafter incremental 3-day window.
            import_rows = list(self._octopus_consumption_data.get("import") or [])
            import_days = 35 if len(import_rows) < 48 else 3
            self._octopus_consumption_data = await refresh_octopus_consumption(
                self.hass,
                self._octopus_consumption_store,
                api_key=api_key,
                octopus_cache=self._octopus_cache,
                greener_cache=self._octopus_greener_cache,
                import_days=import_days,
                export_days=3,
            )
            await self._async_refresh_octopus_analysis()
            await self.async_update_octopus_consumption_sensors()
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.warning("Octopus consumption poll failed: %s", err)
            self._note_octopus_rate_limit(str(err))

    async def async_fetch_octopus_analysis(self, *, force: bool = False) -> dict[str, Any]:
        refreshed = False
        if self._octopus_native_active() and (force or self._octopus_tariff_refresh_due()):
            await self._async_refresh_octopus(force=force)
            refreshed = True
        if self._octopus_greener_enabled() and (force or self._octopus_greener_refresh_due()):
            await self._async_refresh_octopus_greener(force=force)
            refreshed = True
        if self._octopus_greener_enabled() and self.plant.tariff.dynamic.api_key_configured():
            if force or self._octopus_consumption_refresh_due():
                await self._async_refresh_octopus_consumption(force=force)
                refreshed = True
        if refreshed or not self._octopus_analysis_cache or force:
            await self._async_refresh_octopus_analysis()
        if refreshed:
            await self.async_request_refresh()
        return self._octopus_analysis_state() or {}

    def _setup_octopus_consumption_timer(self) -> None:
        if self._unsub_octopus_consumption:
            self._unsub_octopus_consumption()
            self._unsub_octopus_consumption = None
        if not self._octopus_greener_enabled():
            return
        if not self.plant.tariff.dynamic.api_key_configured():
            return
        self._unsub_octopus_consumption = async_track_time_interval(
            self.hass,
            self._octopus_consumption_timer_callback,
            timedelta(minutes=30),
        )

    def _octopus_consumption_timer_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_refresh_octopus_consumption())

    def _setup_octopus_greener_timer(self) -> None:
        if self._unsub_octopus_greener:
            self._unsub_octopus_greener()
            self._unsub_octopus_greener = None
        if not self._octopus_greener_enabled():
            return
        self._unsub_octopus_greener = async_track_time_interval(
            self.hass,
            self._octopus_greener_timer_callback,
            timedelta(hours=2),
        )

    @callback
    def _octopus_greener_timer_callback(self, _now) -> None:
        self.hass.async_create_task(self._async_refresh_octopus_greener())

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
        self._setup_pv_efficiency_timer()
        try:
            await self._async_apply_pv_efficiency_age_derating(refresh_solcast=False)
        except Exception as err:
            _LOGGER.warning("PV efficiency age sync after Solcast save failed: %s", err)
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
        if getattr(self, "_unsub_octopus_greener", None):
            self._unsub_octopus_greener()
            self._unsub_octopus_greener = None
        if getattr(self, "_unsub_octopus_consumption", None):
            self._unsub_octopus_consumption()
            self._unsub_octopus_consumption = None
        if getattr(self, "_unsub_smart_charge", None):
            self._unsub_smart_charge()
            self._unsub_smart_charge = None
        if getattr(self, "_unsub_smart_charge_daily_plan", None):
            self._unsub_smart_charge_daily_plan()
            self._unsub_smart_charge_daily_plan = None
        if getattr(self, "_unsub_smart_charge_entity", None):
            self._unsub_smart_charge_entity()
            self._unsub_smart_charge_entity = None
        if getattr(self, "_unsub_pv_efficiency", None):
            self._unsub_pv_efficiency()
            self._unsub_pv_efficiency = None
        self._teardown_glow_mqtt()
