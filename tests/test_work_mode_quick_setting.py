"""Work Mode quick setting while the EVO's Mode Scheduler is (or isn't) running."""

from types import SimpleNamespace

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator


class _FakeCoordinator:
    def __init__(self, *, scheduler_on: bool) -> None:
        self.plant = SimpleNamespace(plant_schedule=SimpleNamespace(remaining_work_mode="Self Use"))
        self.scheduler_on = scheduler_on
        self.register: str | None = None
        self.pushes = 0

    def inverter_runs_schedule(self) -> bool:
        return True

    def _compile_inverter_schedule(self) -> dict:
        return {"enabled": self.scheduler_on}

    async def _persist(self) -> None:
        pass

    async def async_push_inverter_schedule(self) -> None:
        self.pushes += 1

    async def _set_work_mode(self, option: str) -> None:
        self.register = option

    async def async_request_refresh(self) -> None:
        pass


async def _set(fake: _FakeCoordinator, option: str) -> None:
    await FoxessPlantCoordinator.async_set_work_mode(fake, option)


@pytest.mark.asyncio
async def test_scheduler_running_changes_the_all_day_slot_too() -> None:
    fake = _FakeCoordinator(scheduler_on=True)
    await _set(fake, "Feed-in First")
    assert fake.plant.plant_schedule.remaining_work_mode == "Feed-in First"
    assert fake.pushes == 1
    assert fake.register == "Feed-in First"


@pytest.mark.asyncio
async def test_scheduler_off_only_sets_the_register() -> None:
    fake = _FakeCoordinator(scheduler_on=False)
    await _set(fake, "Back-up")
    assert fake.pushes == 0
    assert fake.plant.plant_schedule.remaining_work_mode == "Self Use"
    assert fake.register == "Back-up"


@pytest.mark.asyncio
async def test_peak_shaving_is_refused_while_the_scheduler_runs() -> None:
    fake = _FakeCoordinator(scheduler_on=True)
    with pytest.raises(HomeAssistantError, match="Mode Scheduler is running"):
        await _set(fake, "Peak Shaving")
    assert fake.register is None
