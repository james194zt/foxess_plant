"""The Glow / meter rate check is skipped on Agile and Tracker: the meter isn't sent half-hourly prices, so its
rate isn't the real price, and comparing it with the API only blocked good charges (seen by a user on Agile)."""

from types import SimpleNamespace

from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator


class FakePlant:
    def __init__(self, agile: bool, meter_p: float) -> None:
        self.plant = SimpleNamespace(
            smart_charge=SimpleNamespace(
                meter_rate_verify_enabled=True,
                meter_rate_entity_id="sensor.glow_import_unit_rate",
                meter_rate_tolerance_p_per_kwh=0.5,
                meter_rate_recheck_minutes=5,
            )
        )
        self._octopus_cache = {"current_import_p_per_kwh": -2.0, "import_rates": []}
        self._agile = agile
        self._meter_p = meter_p

    def _octopus_agile_active(self):
        return self._agile

    def _read_meter_import_rate_sensor(self):
        return self._meter_p, "p/kWh", "sensor.glow_import_unit_rate"


def test_agile_skips_the_meter_check_even_when_it_disagrees() -> None:
    result = FoxessPlantCoordinator._verify_meter_rate_before_charge(FakePlant(agile=True, meter_p=24.5))
    assert result.status == "skipped" and not result.blocks_arm
    assert "Agile" in result.detail


def test_fixed_tariff_still_checks_the_meter() -> None:
    result = FoxessPlantCoordinator._verify_meter_rate_before_charge(FakePlant(agile=False, meter_p=24.5))
    assert result.status == "mismatch" and result.blocks_arm
