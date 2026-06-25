"""Tests for EVO charge-period / remote-control fallback detection."""

from homeassistant.exceptions import HomeAssistantError

from custom_components.foxess_plant.remote_control import is_charge_period_modbus_blocked


def test_blocked_without_illegal_address_in_message() -> None:
    err = HomeAssistantError(
        "Charge-period write failed for registers [(48010, 1), (48011, 5888)]. "
        "EVO 10-H may not allow Modbus writes to 480xx on this firmware."
    )
    assert is_charge_period_modbus_blocked(err)


def test_blocked_when_wrapped_with_plant_hint() -> None:
    err = HomeAssistantError(
        "FoxESS Modbus could not write EVO charge-period registers (480xx). "
        "Details: Charge-period write failed for registers [(48010, 1)]"
    )
    assert is_charge_period_modbus_blocked(err)
