"""SmartCharge grid charges as just-in-time Force Charge slots on the EVO's scheduler."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator


def _window(start_in: timedelta, length: timedelta = timedelta(hours=2), soc_end: float = 79.2) -> dict:
    now = datetime.now(timezone.utc)
    start, end = now + start_in, now + start_in + length
    return {
        "start": "01:00",
        "end": "03:00",
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "soc_end_pct": soc_end,
    }


class _FakeCoordinator:
    """Just enough of the coordinator for _sync_smart_charge_on_inverter."""

    def __init__(self, *, meter_blocks: bool = False, target_max_soc: float | None = None) -> None:
        self.plant = SimpleNamespace(
            smart_charge=SimpleNamespace(
                target_max_soc=target_max_soc, max_target_soc=100.0, max_charge_kw=3.0, meter_rate_recheck_minutes=5
            )
        )
        self._smart_charge_decision: dict = {}
        self._jit_slots: list = []
        self.meter_blocks = meter_blocks
        self.rechecks: list = []

    async def _set_jit_slots(self, slots: list) -> None:
        self._jit_slots = list(slots)

    def _schedule_jit_recheck(self, window, *, has_slots: bool) -> None:
        self.rechecks.append(has_slots)

    def _sync_octopus_current_rates_from_cache(self) -> None:
        pass

    def _verify_meter_rate_before_charge(self):
        return SimpleNamespace(blocks_arm=self.meter_blocks, detail="meter says 24p", to_dict=dict)

    def _schedule_smart_charge_meter_recheck(self, minutes: int) -> None:
        pass

    def _clear_smart_charge_meter_recheck(self) -> None:
        pass


def _decision(action: str, window: dict, target: float | None = None) -> SimpleNamespace:
    charging = action in ("grid_charge", "arbitrage")
    return SimpleNamespace(
        action=action,
        windows=[window] if charging else [],
        next_charge=None if charging else window,
        target_max_soc=target,
        reason="Planned",
    )


async def _sync(fake: _FakeCoordinator, decision: SimpleNamespace) -> list:
    await FoxessPlantCoordinator._sync_smart_charge_on_inverter(fake, decision)
    return fake._jit_slots


@pytest.mark.asyncio
async def test_upcoming_charge_is_put_on_the_inverter_shortly_before() -> None:
    fake = _FakeCoordinator()
    assert await _sync(fake, _decision("idle", _window(timedelta(hours=2)))) == []
    [slot] = await _sync(fake, _decision("idle", _window(timedelta(minutes=20))))
    assert (slot.work_mode, slot.fd_soc, slot.fd_pwr) == ("force_charge", 80, 3000)
    assert "set on the inverter" in fake._smart_charge_decision["reason"]


@pytest.mark.asyncio
async def test_target_is_capped_by_the_smart_charge_max() -> None:
    fake = _FakeCoordinator(target_max_soc=70)
    [slot] = await _sync(fake, _decision("grid_charge", _window(timedelta(minutes=-10)), target=90))
    assert slot.fd_soc == 70


@pytest.mark.asyncio
async def test_meter_check_failure_removes_the_slot() -> None:
    fake = _FakeCoordinator(meter_blocks=True)
    fake._jit_slots = ["previous slot"]
    assert await _sync(fake, _decision("grid_charge", _window(timedelta(minutes=-10)), target=90)) == []
    assert fake._smart_charge_decision["reason"].startswith("Meter check held")


@pytest.mark.asyncio
async def test_slot_is_removed_after_the_window() -> None:
    fake = _FakeCoordinator()
    fake._jit_slots = ["previous slot"]
    assert await _sync(fake, _decision("idle", _window(timedelta(hours=-3)))) == []
