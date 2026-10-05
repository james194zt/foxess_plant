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
