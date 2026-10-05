"""Fox Plant's own inverter alert log: decoding sensor states and raised / cleared events."""

from custom_components.foxess_plant.alert_log import (
    INVERTER_NOT_RESPONDING,
    SOURCE_ALARMS,
    SOURCE_CONNECTION,
    alert_names,
    bms_source,
    diff_events,
    open_alerts,
)


def test_alert_names_per_source() -> None:
    assert alert_names(SOURCE_ALARMS, "None") == set()
    assert alert_names(SOURCE_ALARMS, "Grid power outage; Meter lost") == {"Grid power outage", "Meter lost"}
    assert alert_names(SOURCE_CONNECTION, "Connected") == set()
    assert alert_names(SOURCE_CONNECTION, "Disconnected") == {INVERTER_NOT_RESPONDING}
    assert alert_names(bms_source(2), "9") == {"Battery fault 2 bit 0 (0x0001)", "Battery fault 2 bit 3 (0x0008)"}
    assert alert_names(bms_source(2), "0") == set()


def test_no_reading_is_not_a_clear() -> None:
    for state in ("unknown", "unavailable", None):
        assert alert_names(SOURCE_ALARMS, state) is None
        assert alert_names(bms_source(1), state) is None


def test_events_and_open_alerts() -> None:
    raised = diff_events(set(), {"Meter lost"}, "2026-10-01T10:00:00+00:00", SOURCE_ALARMS)
    assert raised == [{"t": "2026-10-01T10:00:00+00:00", "action": "raised", "name": "Meter lost", "source": "alarms"}]
    bms = diff_events(set(), {"Battery fault 1 bit 3 (0x0008)"}, "2026-10-01T11:00:00+00:00", bms_source(1))
    cleared = diff_events({"Meter lost"}, set(), "2026-10-03T09:00:00+00:00", SOURCE_ALARMS)
    assert open_alerts(raised + bms) == {"Meter lost": "alarms", "Battery fault 1 bit 3 (0x0008)": "bms_1"}
    assert open_alerts(raised + bms + cleared) == {"Battery fault 1 bit 3 (0x0008)": "bms_1"}
