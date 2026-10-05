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
    # Named from the EVO manual's BMS table; bits it doesn't name keep their raw bit
    assert alert_names(bms_source(1), "3") == {
        "Battery BS1 E01: Communication fault with PCS (EXT COM)",
        "Battery BS1 E02: Internal communication fault (INT COM)",
    }
    assert alert_names(bms_source(2), "4") == {"Battery BS2 bit 2 (0x0004)"}
    assert alert_names(bms_source(2), "256") == {"Battery BS2 bit 8 (0x0100)"}
    assert alert_names(bms_source(2), "0") == set()


def test_no_reading_is_not_a_clear() -> None:
    for state in ("unknown", "unavailable", None):
        assert alert_names(SOURCE_ALARMS, state) is None
        assert alert_names(bms_source(1), state) is None


def test_events_and_open_alerts() -> None:
    raised = diff_events(set(), {"Meter lost"}, "2026-10-01T10:00:00+00:00", SOURCE_ALARMS)
    assert raised == [{"t": "2026-10-01T10:00:00+00:00", "action": "raised", "name": "Meter lost", "source": "alarms"}]
    uv = "Battery BS1 E08: Under voltage fault (UV)"
    bms = diff_events(set(), {uv}, "2026-10-01T11:00:00+00:00", bms_source(1))
    cleared = diff_events({"Meter lost"}, set(), "2026-10-03T09:00:00+00:00", SOURCE_ALARMS)
    assert open_alerts(raised + bms) == {"Meter lost": "alarms", uv: "bms_1"}
    assert open_alerts(raised + bms + cleared) == {uv: "bms_1"}


def test_python_and_panel_bms_tables_match() -> None:
    import re
    from pathlib import Path

    from custom_components.foxess_plant.alert_log import BMS_FAULT_BITS

    guide = Path("custom_components/foxess_plant/www/fox-alarm-guide.js").read_text(encoding="utf-8")
    block = guide.split("export const FOX_BMS_FAULT_BITS = [", 1)[1].split("];", 1)[0]
    rows = [re.findall(r'"([^"]*)"|null', row) for row in block.split("],")]
    js = [[cell or None for cell in row] for row in rows if row]
    assert js == BMS_FAULT_BITS
