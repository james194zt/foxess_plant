"""Control keys must match entity ids exactly; panel keys tolerate longer EVO ids."""

import pytest

from custom_components.foxess_plant.discovery import (
    _entity_id_matches_exact_suffix,
    _entity_id_matches_panel_suffix,
    resolve_entity_id,
)


def test_max_soc_does_not_match_max_soc_from_grid() -> None:
    assert _entity_id_matches_exact_suffix("number.evo_10_max_soc", "max_soc")
    assert not _entity_id_matches_exact_suffix("number.evo_10_max_soc_from_grid", "max_soc")
    assert _entity_id_matches_exact_suffix("number.evo_10_max_soc_from_grid", "max_soc_from_grid")


def test_panel_suffix_still_matches_long_evo_ids() -> None:
    assert _entity_id_matches_panel_suffix("sensor.foxess_pv_power_evo_10", "pv_power")


@pytest.mark.asyncio
async def test_installer_rows_read_the_sensor_not_the_writable_number(hass) -> None:
    # The fork's EVO has both: a kW sensor and a W number with the same suffix
    hass.states.async_set("number.evo_10_peak_shaving_export_limit", "13000", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.evo_10_peak_shaving_export_limit", "13.0", {"unit_of_measurement": "kW"})
    hass.states.async_set("select.evo_10_mppt_scan", "Off")
    hass.states.async_set("sensor.evo_10_mppt_scan", "0")

    assert resolve_entity_id(hass, {}, "peak_shaving_export_limit") == "sensor.evo_10_peak_shaving_export_limit"
    assert resolve_entity_id(hass, {}, "mppt_scan") == "sensor.evo_10_mppt_scan"


@pytest.mark.asyncio
async def test_installer_row_falls_back_to_the_number_without_a_sensor(hass) -> None:
    hass.states.async_set("number.evo_10_max_charge_current", "50.0", {"unit_of_measurement": "A"})

    assert resolve_entity_id(hass, {}, "max_charge_current") == "number.evo_10_max_charge_current"
