"""Tests for Fox Cloud battery warmup parsing."""

from custom_components.foxess_plant.battery_warmup import parse_battery_heating_result

STOPPED_STATE = "The battery is in a stopped warm up state"


def test_parse_battery_warmup_state_string() -> None:
    parsed = parse_battery_heating_result(
        {
            "dataList": [
                {"name": "batteryWarmUpEnable", "value": "enable"},
                {
                    "name": "batteryWarmUpState",
                    "enumList": [STOPPED_STATE],
                    "value": STOPPED_STATE,
                },
            ]
        }
    )
    assert parsed["enabled"] is True
    assert parsed["state"] == STOPPED_STATE


def test_parse_battery_warmup_state_enum_index() -> None:
    parsed = parse_battery_heating_result(
        {
            "dataList": [
                {"name": "batteryWarmUpFunctionEnableFlag", "value": "enable"},
                {
                    "name": "batteryWarmUpState",
                    "enumList": [STOPPED_STATE, "The battery is in the warm up state"],
                    "value": "0",
                },
            ]
        }
    )
    assert parsed["enabled"] is True
    assert parsed["state"] == STOPPED_STATE


def test_parse_battery_warmup_state_case_insensitive_name() -> None:
    parsed = parse_battery_heating_result(
        {
            "dataList": [
                {"name": "BatteryWarmUpState", "value": STOPPED_STATE},
            ]
        }
    )
    assert parsed["state"] == STOPPED_STATE
