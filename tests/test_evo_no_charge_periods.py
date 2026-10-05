"""The EVO has no charge periods: Fox Plant must never write foxess_modbus charge periods to it.

foxess_modbus maps EVO "charge periods" onto Mode Scheduler slots 1-2, which would overwrite the schedule
Fox Plant keeps on the inverter.
"""

from types import SimpleNamespace

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.foxess_plant import coordinator as coordinator_module
from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator


class _FakeEvo:
    def __init__(self) -> None:
        self.plant = SimpleNamespace(control_active=True, entity_map={})

    def _is_evo(self) -> bool:
        return True

    def inverter_runs_schedule(self) -> bool:
        return False  # e.g. foxess_modbus without the Mode Scheduler actions


@pytest.fixture(autouse=True)
def _no_charge_period_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fail(*args, **kwargs) -> None:
        raise AssertionError("charge periods written to an EVO")

    monkeypatch.setattr(coordinator_module, "apply_charge_periods", _fail)
    monkeypatch.setattr(
        "custom_components.foxess_plant.schedule_runner.resolve_desired_bundle", lambda coordinator: None
    )


@pytest.mark.asyncio
async def test_saving_charge_periods_on_an_evo_is_refused() -> None:
    with pytest.raises(HomeAssistantError, match="no charge periods"):
        await FoxessPlantCoordinator.async_save_charge_schedule(_FakeEvo(), [])


@pytest.mark.asyncio
async def test_apply_without_the_scheduler_actions_does_not_fall_back_to_charge_periods() -> None:
    with pytest.raises(HomeAssistantError, match="set_evo_schedule"):
        await FoxessPlantCoordinator.async_apply_desired(_FakeEvo(), strict=True)
    # Not strict (e.g. the minute timer): just a warning, still no charge-period write
    await FoxessPlantCoordinator.async_apply_desired(_FakeEvo())
