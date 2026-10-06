"""The Overview "Warming up" pill: only on a fresh Fox Cloud report of warming, with the battery still cold."""

from datetime import timedelta
from types import SimpleNamespace

from homeassistant.util import dt as dt_util

from custom_components.foxess_plant.battery_warmup import warmup_state_is_warming
from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator


def test_state_text() -> None:
    assert warmup_state_is_warming("The battery is in a warm up state")
    assert warmup_state_is_warming("The battery is in a self warming state")
    assert not warmup_state_is_warming("The battery is in a standby state")
    assert not warmup_state_is_warming("Ready warm up stopped")
    assert not warmup_state_is_warming(None)


def _warming(checked_ago: timedelta, temp: float) -> bool:
    fake = SimpleNamespace(_battery_warmup_checked_at=dt_util.utcnow() - checked_ago)
    return FoxessPlantCoordinator._battery_warmup_warming_now(
        fake, {"state": "The battery is in a warm up state", "battery_temperature_c": temp, "end_temperature": 10}
    )


def test_pill_needs_a_fresh_report_and_a_cold_battery() -> None:
    assert _warming(timedelta(minutes=4), 3.0)
    assert not _warming(timedelta(minutes=30), 3.0)  # old report: don't claim it's still warming
    assert not _warming(timedelta(minutes=4), 19.0)  # battery well above the end temperature
