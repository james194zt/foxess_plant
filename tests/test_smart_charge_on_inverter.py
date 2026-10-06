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

    def __init__(
        self,
        *,
        meter_blocks: bool = False,
        target_max_soc: float | None = None,
        model: str | None = None,
        soc: float | None = 90.0,
    ) -> None:
        self.model = model
        self.soc = soc
        self._export_done_window = None
        self._unsub_export_watch = None
        self.watching: list = []
        self.plant = SimpleNamespace(
            smart_charge=SimpleNamespace(
                target_max_soc=target_max_soc,
                max_target_soc=100.0,
                max_charge_kw=3.0,
                max_discharge_kw=None,
                export_min_soc=40.0,
                meter_rate_recheck_minutes=5,
            )
        )
        self._smart_charge_decision: dict = {}
        self._jit_slots: list = []
        self.meter_blocks = meter_blocks
        self.rechecks: list = []

    def _entity_state(self, key: str) -> str | None:
        return self.model if key == "pcs_model_name" else None

    def _entity_float(self, key: str) -> float | None:
        return self.soc if key == "battery_soc" else None

    def _export_cut_off_reached(self, cut_off: int) -> bool:
        return FoxessPlantCoordinator._export_cut_off_reached(self, cut_off)

    def _watch_export_cut_off(self, cut_off, window_key) -> None:
        self.watching.append((cut_off, window_key))

    def async_update_listeners(self) -> None:
        pass

    async def _set_jit_slots(self, slots: list) -> None:
        self._jit_slots = list(slots)

    def _schedule_jit_recheck(self, windows) -> None:
        self.rechecks.append(windows)

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
        next_export=None,
        discharge_window=None,
        target_max_soc=target,
        reason="Planned",
    )


def _export_decision(action: str, window: dict) -> SimpleNamespace:
    exporting = action == "export_discharge"
    return SimpleNamespace(
        action=action,
        windows=[window] if exporting else [],
        next_charge=None,
        next_export=None if exporting else window,
        discharge_window=window if exporting else None,
        target_max_soc=None,
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
async def test_upcoming_export_is_a_force_discharge_slot_at_full_inverter_power() -> None:
    fake = _FakeCoordinator(model="EVO 10-5-H")
    [slot] = await _sync(fake, _export_decision("idle", _window(timedelta(minutes=20), soc_end=52.7)))
    # Ends at the plan's end SoC (rounded down, 52): the inverter only stops below its cut-off, so the cut-off
    # is 53. The slot power caps total output, so use the full rating.
    assert (slot.work_mode, slot.fd_soc, slot.fd_pwr) == ("force_discharge", 53, 5000)
    assert "Export" in fake._smart_charge_decision["reason"]
    assert fake.watching[-1][0] == 53  # watched so it comes off at the cut-off


@pytest.mark.asyncio
async def test_export_power_falls_back_without_a_model() -> None:
    fake = _FakeCoordinator()
    [slot] = await _sync(fake, _export_decision("idle", _window(timedelta(minutes=20), soc_end=52.7)))
    assert slot.fd_pwr == 3000  # max charge power, as no discharge power is set


@pytest.mark.asyncio
async def test_export_never_goes_below_the_export_floor() -> None:
    fake = _FakeCoordinator()
    [slot] = await _sync(fake, _export_decision("export_discharge", _window(timedelta(minutes=-5), soc_end=20.0)))
    assert slot.fd_soc == 41  # stops below 41, i.e. at the 40 % floor


@pytest.mark.asyncio
async def test_export_that_reached_its_cut_off_comes_off_and_stays_off() -> None:
    # Past its cut-off the slot would hold the battery and run the house from the grid at peak price
    fake = _FakeCoordinator(soc=52.0)
    window = _window(timedelta(minutes=-30), soc_end=52.7)
    fake._jit_slots = ["export slot"]
    assert await _sync(fake, _export_decision("export_discharge", window)) == []
    assert fake._export_done_window == window["start_utc"]
    fake.soc = 60.0  # e.g. solar tops it up: the same export isn't restarted
    assert await _sync(fake, _export_decision("export_discharge", window)) == []
    assert fake.watching[-1] == (None, window["start_utc"])


@pytest.mark.asyncio
async def test_finishing_an_export_keeps_any_charge_slot() -> None:
    from custom_components.foxess_plant.inverter_schedule import InverterSlot

    fake = _FakeCoordinator(soc=52.0)
    charge = InverterSlot(start="01:00", end="03:00", work_mode="force_charge", fd_soc=80, fd_pwr=3000)
    export = InverterSlot(start="17:00", end="19:00", work_mode="force_discharge", fd_soc=53, fd_pwr=5000)
    fake._jit_slots = [charge, export]
    await FoxessPlantCoordinator._async_finish_export(fake, "window-1", 53)
    assert fake._jit_slots == [charge]
    assert fake._export_done_window == "window-1"
    assert "Export finished" in fake._smart_charge_decision["reason"]


@pytest.mark.asyncio
async def test_slot_is_removed_after_the_window() -> None:
    fake = _FakeCoordinator()
    fake._jit_slots = ["previous slot"]
    assert await _sync(fake, _decision("idle", _window(timedelta(hours=-3)))) == []
