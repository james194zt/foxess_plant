"""StormSafe holding the battery with a rolling Force Charge slot on the EVO's scheduler."""

from datetime import timedelta
from types import MethodType, SimpleNamespace

import pytest
from homeassistant.util import dt as dt_util

from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator
from custom_components.foxess_plant.models import ChargePeriodConfig


def _periods(grid: bool) -> list[ChargePeriodConfig]:
    return [ChargePeriodConfig(enable_force_charge=True, enable_charge_from_grid=grid)]


class _FakeCoordinator:
    def __init__(self, *, armed: bool = True, grid: bool = True, mode: str = "storm") -> None:
        self.plant = SimpleNamespace(
            override=SimpleNamespace(active=armed, mode=mode, periods=_periods(grid)),
            storm_prep=SimpleNamespace(target_max_soc=95),
            outage_prep=SimpleNamespace(target_max_soc=100),
            forecast_prep=SimpleNamespace(target_max_soc=80),
            smart_charge=SimpleNamespace(max_charge_kw=6.0),
        )
        self._storm_slots: list = []
        self._storm_slots_until = None
        self.pushes = 0
        self.rc_cleared = 0
        self._prep_hold_config = MethodType(FoxessPlantCoordinator._prep_hold_config, self)
        self.storm_runs_on_inverter = MethodType(FoxessPlantCoordinator.storm_runs_on_inverter, self)

    def inverter_runs_schedule(self) -> bool:
        return True

    async def _set_extra_slots(self, *, storm=None, jit=None) -> bool:
        self._storm_slots = list(storm)
        self.pushes += 1
        return True

    async def _clear_remote_control_for_restore(self) -> None:
        self.rc_cleared += 1


async def _sync(fake: _FakeCoordinator) -> None:
    await FoxessPlantCoordinator._sync_storm_on_inverter(fake)


@pytest.mark.asyncio
async def test_armed_storm_holds_the_battery_on_the_inverter() -> None:
    fake = _FakeCoordinator()
    await _sync(fake)
    [slot] = fake._storm_slots[:1]
    assert (slot.work_mode, slot.fd_soc, slot.fd_pwr) == ("force_charge", 95, 6000)
    assert fake.rc_cleared == 1


@pytest.mark.asyncio
async def test_hold_is_only_rewritten_when_it_needs_extending() -> None:
    fake = _FakeCoordinator()
    await _sync(fake)
    await _sync(fake)
    assert fake.pushes == 1
    fake._storm_slots_until = dt_util.now() + timedelta(minutes=90)  # under 2 hours left
    await _sync(fake)
    assert fake.pushes == 2


@pytest.mark.asyncio
async def test_slot_removed_when_storm_disarms() -> None:
    fake = _FakeCoordinator()
    await _sync(fake)
    fake.plant.override.active = False
    await _sync(fake)
    assert fake._storm_slots == []


@pytest.mark.parametrize(("mode", "target"), [("outage", 100), ("forecast", 80)])
@pytest.mark.asyncio
async def test_outage_and_forecast_prep_hold_at_their_own_target(mode: str, target: int) -> None:
    fake = _FakeCoordinator(mode=mode)
    await _sync(fake)
    assert fake._storm_slots[0].fd_soc == target


@pytest.mark.asyncio
async def test_smart_charge_override_is_not_a_hold() -> None:
    fake = _FakeCoordinator(mode="smart_charge")
    await _sync(fake)
    assert fake._storm_slots == []


@pytest.mark.asyncio
async def test_pv_only_storm_stays_off_the_inverter() -> None:
    fake = _FakeCoordinator(grid=False)
    await _sync(fake)
    assert fake._storm_slots == [] and fake.pushes == 0
