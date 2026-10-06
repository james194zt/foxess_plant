"""A warm-up save shows the saved settings until Fox Cloud reports them, instead of the stale read-back."""

from datetime import timedelta
from types import SimpleNamespace

from homeassistant.util import dt as dt_util

from custom_components.foxess_plant.battery_warmup import warmup_settings_match
from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator

SAVED = {
    "enabled": True,
    "start_temperature": 3,
    "end_temperature": 12,
    "slots": [
        {"enabled": True, "start": "02:00", "end": "05:00"},
        {"enabled": False, "start": "00:00", "end": "00:00"},
        {"enabled": False, "start": "00:00", "end": "00:00"},
    ],
}
OLD = {**SAVED, "start_temperature": 1, "end_temperature": 10, "state": "standby", "ranges": {"start_min": 1}}


def _fake(since_ago: timedelta) -> SimpleNamespace:
    return SimpleNamespace(
        _battery_warmup_pending={"saved": SAVED, "since": dt_util.utcnow() - since_ago},
        _battery_warmup_confirm_warning=None,
        _battery_warmup_live={},
    )


def test_times_compare_whatever_their_format() -> None:
    reported = {**SAVED, "slots": [{"enabled": True, "start": "2:00", "end": "5:0"}, {}, {}]}
    assert warmup_settings_match(SAVED, reported)


def test_stale_read_back_right_after_a_save_shows_the_saved_settings() -> None:
    fake = _fake(timedelta(seconds=5))
    shown = FoxessPlantCoordinator._set_warmup_reported(fake, OLD)
    assert (shown["start_temperature"], shown["end_temperature"]) == (3, 12)
    assert shown["state"] == "standby"  # the rest of Fox Cloud's read-back is kept
    assert fake._battery_warmup_pending  # still waiting


def test_confirmed_save_clears_the_wait() -> None:
    fake = _fake(timedelta(seconds=40))
    reported = {**SAVED, "state": "standby"}
    assert FoxessPlantCoordinator._set_warmup_reported(fake, reported) is reported
    assert fake._battery_warmup_pending is None
    assert fake._battery_warmup_confirm_warning is None


def test_never_confirmed_shows_the_read_back_with_a_warning() -> None:
    fake = _fake(timedelta(minutes=4))
    assert FoxessPlantCoordinator._set_warmup_reported(fake, OLD) is OLD
    assert fake._battery_warmup_pending is None
    assert "Refresh from inverter" in fake._battery_warmup_confirm_warning
