"""Plant coordinator — central control for charge periods and drift detection."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .charge_period import apply_charge_periods
from .const import (
    EVENT_BASELINE_RESTORED,
    EVENT_CONTROL_DRIFT,
    EVENT_EXTERNAL_WRITE,
    EVENT_PERIOD_APPLIED,
    EVENT_PERIOD_APPLY_FAILED,
    EVENT_STORM_ARMED,
    EVENT_STORM_DISARMED,
    MODE_BASELINE,
    MODE_OVERRIDE,
    MODE_STORM,
    MODE_TARIFF,
)
from .models import ChargePeriodConfig, OverrideState, PlantConfig

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


class FoxessPlantCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinates plant policy, Modbus writes, and drift detection."""

    config_entry: ConfigEntry
    plant: PlantConfig
    _unsub_drift: callable | None = None
    _applying: bool = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.config_entry = entry
        self.plant = PlantConfig.from_entry_data(entry.data)
        super().__init__(
            hass,
            _LOGGER,
            name=f"FoxESS Plant {entry.title}",
            update_interval=UPDATE_INTERVAL,
        )

    async def async_config_entry_first_refresh(self) -> None:
        await super().async_config_entry_first_refresh()
        self._setup_drift_timer()
        if self.plant.control_active:
            try:
                await self.async_apply_desired(force=True)
            except HomeAssistantError as err:
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
        self._setup_drift_timer()

    async def _persist(self) -> None:
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=self.plant.to_entry_data(),
        )

    def get_plant_state(self) -> dict[str, Any]:
        desired = [p.to_dict() for p in self.plant.desired_periods()]
        actual = self._read_actual_periods()
        drift = self._compute_drift(desired, actual)
        return {
            "plant_id": self.config_entry.entry_id,
            "title": self.config_entry.title,
            "inverter": self.plant.inverter_target,
            "control_active": self.plant.control_active,
            "mode": self.plant.plant_mode(),
            "override_active": self.plant.override.active,
            "override_reason": self.plant.override.reason,
            "desired_periods": desired,
            "actual_periods": actual,
            "drift": drift,
            "entity_map": self.plant.entity_map,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        state = self.get_plant_state()
        return state

    def _entity_state(self, key: str) -> str | None:
        entity_id = self.plant.entity_map.get(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        return state.state if state else None

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
        self.plant.override = OverrideState()
        await self._persist()
        await self.async_apply_desired()
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
        if mode == MODE_STORM:
            self._fire(EVENT_STORM_ARMED, {"reason": reason})
        elif mode == MODE_TARIFF:
            self._fire(EVENT_STORM_ARMED, {"reason": reason, "mode": MODE_TARIFF})

    async def async_disarm_override(self) -> None:
        was_storm = self.plant.override.mode == MODE_STORM
        self.plant.override = OverrideState()
        await self._persist()
        await self.async_apply_desired()
        if was_storm:
            self._fire(EVENT_STORM_DISARMED, {})
        self._fire(EVENT_BASELINE_RESTORED, {})

    async def async_arm_storm_prep(
        self,
        periods: list[ChargePeriodConfig] | None,
        reason: str = "storm_prep",
    ) -> None:
        use_periods = periods if periods else self.plant.baseline_periods
        await self.async_set_override_periods(use_periods, MODE_STORM, reason)

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
            {
                "desired": state["desired_periods"],
                "actual": state["actual_periods"],
            },
        )
        self._fire(
            EVENT_EXTERNAL_WRITE,
            {
                "desired": state["desired_periods"],
                "actual": state["actual_periods"],
            },
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
