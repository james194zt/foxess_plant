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
from .charge_period import apply_charge_periods
from .const import (
    ANALYTICS_ENTITY_SUFFIXES,
    AUTOMATION_MODES,
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
from .models import ChargePeriodConfig, OverrideState, PlantConfig

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

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.config_entry = entry
        self.plant = PlantConfig.from_entry_data(entry.data)
        self._active_storm_triggers = set()
        self._active_outage_triggers = set()
        self._forecast_armed = False
        super().__init__(
            hass,
            _LOGGER,
            name=f"FoxESS Plant {entry.title}",
            update_interval=UPDATE_INTERVAL,
        )

    async def async_config_entry_first_refresh(self) -> None:
        self._sync_trigger_membership()
        self.setup_trigger_listeners()
        await super().async_config_entry_first_refresh()
        self._setup_drift_timer()
        try:
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
            if self._is_trigger_active(eid)
        }
        self._active_outage_triggers = {
            eid
            for eid in self.plant.outage_prep.trigger_entities
            if self._is_trigger_active(eid)
        }

    def _is_trigger_active(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        return state.state.lower() in TRIGGER_ON_STATES

    async def _async_handle_trigger_event(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        if not entity_id or not self.plant.control_active:
            return

        if entity_id in self.plant.storm_prep.trigger_entities:
            if self._is_trigger_active(entity_id):
                self._active_storm_triggers.add(entity_id)
            else:
                self._active_storm_triggers.discard(entity_id)

        if entity_id in self.plant.outage_prep.trigger_entities:
            if self._is_trigger_active(entity_id):
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
        entity_id = self.plant.entity_map.get("max_soc")
        if not entity_id:
            return
        await self.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id, "value": value},
            blocking=True,
        )

    async def _persist(self) -> None:
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=self.plant.to_entry_data(),
        )

    def get_plant_state(self) -> dict[str, Any]:
        desired = [p.to_dict() for p in self.plant.desired_periods()]
        actual = self._read_actual_periods()
        drift = self._compute_drift(desired, actual)
        analytics = self._read_analytics()
        return {
            "plant_id": self.config_entry.entry_id,
            "title": self.config_entry.title,
            "inverter": self.plant.inverter_target,
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
            "active_storm_triggers": sorted(self._active_storm_triggers),
            "active_outage_triggers": sorted(self._active_outage_triggers),
            "forecast_armed": self._forecast_armed,
            "tariff_modes": sorted(self.plant.tariff_modes.keys()),
            "storm_prep": self.plant.storm_prep.to_dict(),
            "outage_prep": self.plant.outage_prep.to_dict(),
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

    def _read_identity(self) -> dict[str, str | None]:
        """PCS/BMS identity and firmware from discovered foxess_modbus entities."""
        return {
            key: self._entity_state(key)
            for key in IDENTITY_ENTITY_SUFFIXES
            if self.plant.entity_map.get(key)
        }

    async def _async_update_data(self) -> dict[str, Any]:
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
            await apply_charge_periods(self.hass, self.plant.inverter_target, periods)
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
    ) -> None:
        """Persist storm prep from the Fox Plant panel."""
        periods = [ChargePeriodConfig.from_dict(p) for p in charge_periods]
        data = dict(self.config_entry.data)
        data[CONF_STORM_PREP] = {
            "enabled": enabled,
            "trigger_entities": list(trigger_entities),
            "charge_periods": [p.to_dict() for p in periods],
            "target_max_soc": target_max_soc,
        }
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        self.update_plant_config(PlantConfig.from_entry_data(data))
        await self._sync_automation_policy()
        await self.async_request_refresh()

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
        if self._unsub_triggers:
            self._unsub_triggers()
            self._unsub_triggers = None
