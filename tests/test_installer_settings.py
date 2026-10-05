"""Installer settings shown read-only under Device → Realtime."""

from custom_components.foxess_plant.installer_settings import (
    GRID_STANDARDS,
    grid_standard_label,
    installer_settings_rows,
)


def test_grid_standard_names_come_from_the_protocol_table() -> None:
    assert grid_standard_label("3") == "G99_UK (UK)"
    assert grid_standard_label(7) == "VDE4105_DE (Germany)"
    assert grid_standard_label("73.0") == "G99_NI (Northern Ireland)"
    assert grid_standard_label(250) == "Code 250"
    assert grid_standard_label("unknown") is None
    assert len(GRID_STANDARDS) == 98


def test_rows_skip_settings_the_inverter_does_not_have() -> None:
    states = {"grid_standard_code": "3", "max_active_power": "3.68", "rated_power": "unavailable"}
    rows = installer_settings_rows(states.get)
    assert [r["key"] for r in rows] == ["grid_standard_code", "max_active_power"]
    assert rows[0]["value"] == "G99_UK (UK)"
    assert rows[1]["value"] == "3.68 kW"


def test_coded_settings_are_named() -> None:
    states = {"meter1_type": "2", "meter2_type": "0", "eps_output_mode": "3", "eps_frequency_setting": "1",
              "mppt_scan": "0", "meter_compensation": "0", "peak_shaving_threshold_soc": "0"}
    values = {r["key"]: r["value"] for r in installer_settings_rows(states.get)}
    assert values == {
        "meter1_type": "CT",
        "meter2_type": "Off",
        "eps_output_mode": "UPS mode",
        "eps_frequency_setting": "50 Hz",
        "mppt_scan": "Off",
        "meter_compensation": "0 W",
        "peak_shaving_threshold_soc": "0 %",
    }
