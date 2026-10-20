"""Zero export: Export Power Limit 0 W while the export price is negative, then exactly the saved value back."""

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.foxess_plant import zero_export
from custom_components.foxess_plant.zero_export import (
    ENGAGE,
    HOLD,
    RELEASE,
    ZeroExportController,
    decide,
    find_export_limit_entity,
)

NUMBER = "number.evo_10_export_power_limit"
SENSOR = "sensor.evo_10_installer_export_power_limit"


@pytest.mark.parametrize(
    ("enabled", "price", "active", "expected"),
    [
        (True, -1.5, False, ENGAGE),
        (True, -1.5, True, HOLD),
        (True, 0.0, True, RELEASE),  # 0p isn't negative: exporting costs nothing
        (True, 13.0, False, HOLD),
        (True, None, True, RELEASE),  # unknown price: fail safe, export allowed again
        (True, None, False, HOLD),
        (False, -5.0, True, RELEASE),  # turned off / Release Control
        (False, -5.0, False, HOLD),
    ],
)
def test_decide(enabled, price, active, expected) -> None:
    assert decide(enabled=enabled, price_p=price, active=active) == expected


def _inverter(hass) -> str:
    entry = MockConfigEntry(domain="foxess_modbus")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={("foxess_modbus", "evo")})
    reg = er.async_get(hass)
    # The read-only installer sensor ends the same way and must not be picked
    reg.async_get_or_create(
        "sensor", "foxess_modbus", "inst", suggested_object_id="evo_10_installer_export_power_limit",
        device_id=device.id, config_entry=entry,
    )
    reg.async_get_or_create(
        "number", "foxess_modbus", "num", suggested_object_id="evo_10_export_power_limit",
        device_id=device.id, config_entry=entry,
    )
    return device.id


@pytest.mark.asyncio
async def test_finds_the_writable_number_not_the_installer_sensor(hass) -> None:
    device_id = _inverter(hass)
    assert find_export_limit_entity(hass, device_id) == NUMBER


@pytest.mark.asyncio
async def test_engage_saves_the_limit_then_writes_zero_and_release_puts_it_back(hass, hass_storage) -> None:
    device_id = _inverter(hass)
    hass.states.async_set(NUMBER, "15000")
    calls = async_mock_service(hass, "number", "set_value")
    ctrl = ZeroExportController(hass, "e1")

    assert await ctrl.async_apply(enabled=True, price_p=-2.0, device_id=device_id)
    assert [c.data["value"] for c in calls] == [0]
    saved = hass_storage["foxess_plant.zero_export.e1"]["data"]
    assert saved["active"] is True and saved["original_w"] == 15000.0 and saved["entity_id"] == NUMBER

    hass.states.async_set(NUMBER, "0")
    assert await ctrl.async_apply(enabled=True, price_p=-1.0, device_id=device_id)  # still negative: nothing
    assert len(calls) == 1

    assert await ctrl.async_apply(enabled=True, price_p=4.0, device_id=device_id)
    assert [c.data["value"] for c in calls] == [0, 15000.0]
    assert hass_storage["foxess_plant.zero_export.e1"]["data"]["active"] is False


@pytest.mark.asyncio
async def test_restart_mid_slot_still_puts_the_saved_limit_back(hass, hass_storage) -> None:
    device_id = _inverter(hass)
    hass_storage["foxess_plant.zero_export.e1"] = {
        "version": 1,
        "key": "foxess_plant.zero_export.e1",
        "data": {"active": True, "original_w": 12000.0, "since": "2026-10-20T12:00:00+00:00", "entity_id": NUMBER},
    }
    hass.states.async_set(NUMBER, "0")
    calls = async_mock_service(hass, "number", "set_value")
    ctrl = ZeroExportController(hass, "e1")  # a fresh one, as after a restart

    assert await ctrl.async_apply(enabled=True, price_p=6.0, device_id=device_id)
    assert [c.data["value"] for c in calls] == [12000.0]  # what was there, never the 15000 maximum


@pytest.mark.asyncio
async def test_inverter_unavailable_means_retry_without_taking_over(hass, hass_storage) -> None:
    device_id = _inverter(hass)
    hass.states.async_set(NUMBER, "unavailable")
    calls = async_mock_service(hass, "number", "set_value")
    ctrl = ZeroExportController(hass, "e1")

    assert not await ctrl.async_apply(enabled=True, price_p=-3.0, device_id=device_id)
    assert calls == []
    assert ctrl.state.active is False
    assert ctrl.last_error


@pytest.mark.asyncio
async def test_already_zero_is_left_alone(hass) -> None:
    device_id = _inverter(hass)
    hass.states.async_set(NUMBER, "0")
    calls = async_mock_service(hass, "number", "set_value")
    ctrl = ZeroExportController(hass, "e1")

    assert await ctrl.async_apply(enabled=True, price_p=-3.0, device_id=device_id)
    assert calls == [] and ctrl.state.active is False


@pytest.mark.asyncio
async def test_failed_restores_notify_after_a_few_tries(hass, hass_storage, monkeypatch) -> None:
    device_id = _inverter(hass)
    hass.states.async_set(NUMBER, "0")
    hass_storage["foxess_plant.zero_export.e1"] = {
        "version": 1,
        "key": "foxess_plant.zero_export.e1",
        "data": {"active": True, "original_w": 15000.0, "since": None, "entity_id": NUMBER},
    }
    ctrl = ZeroExportController(hass, "e1")

    async def refuse(*_args, **_kwargs):
        raise RuntimeError("changed less than 60 s ago")

    monkeypatch.setattr(ctrl, "_async_set", refuse)
    notes = []
    monkeypatch.setattr(ctrl, "_notify", lambda action, err: notes.append(action))
    for _ in range(zero_export.NOTIFY_AFTER_FAILURES):
        assert not await ctrl.async_apply(enabled=False, price_p=None, device_id=device_id)
    assert notes == [RELEASE]
    assert ctrl.state.active is True  # still owed a restore; the saved value is kept
