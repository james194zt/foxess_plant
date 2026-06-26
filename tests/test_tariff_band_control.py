"""Tests for tariff band → inverter schedule bundles."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.foxess_plant.models import TariffConfig
from custom_components.foxess_plant.schedule_runner import (
    SOURCE_TARIFF,
    bundle_from_tariff_band,
    resolve_desired_bundle,
    resolve_tariff_band_bundle,
)
from custom_components.foxess_plant.tariff_schedule import TariffBandConfig, TariffScheduleConfig


def test_bundle_from_tariff_band_force_charge():
    band = TariffBandConfig(
        work_mode="Feed-in First",
        enable_force_charge=True,
    )
    bundle = bundle_from_tariff_band(
        band,
        min_soc=10,
        min_soc_on_grid=10,
        max_soc=100,
        band_label="Band B",
    )
    assert bundle.work_mode == "Feed-in First"
    assert bundle.force_charge is True
    assert bundle.charge_from_grid is True
    assert bundle.source == SOURCE_TARIFF
    assert bundle.label == "Band B"


def test_resolve_tariff_band_bundle_for_hour():
    schedule = TariffScheduleConfig(
        hours=[0] * 12 + [1] * 12,
        bands=[
            TariffBandConfig(work_mode="Self Use"),
            TariffBandConfig(work_mode="Back-up", enable_force_charge=True),
            TariffBandConfig(),
            TariffBandConfig(),
        ],
    )
    tariff = TariffConfig(apply_band_inverter_control=True, schedule=schedule)
    plant = SimpleNamespace(
        tariff=tariff,
        entity_map={},
        virtual_soc=SimpleNamespace(max_soc=None),
    )
    coordinator = SimpleNamespace(
        plant=plant,
        hass=MagicMock(),
    )

    morning = resolve_tariff_band_bundle(coordinator, when=datetime(2026, 5, 28, 8, 30))
    assert morning is not None
    assert morning.work_mode == "Self Use"
    assert morning.label == "Band A"

    afternoon = resolve_tariff_band_bundle(coordinator, when=datetime(2026, 5, 28, 14, 0))
    assert afternoon is not None
    assert afternoon.work_mode == "Back-up"
    assert afternoon.force_charge is True
    assert afternoon.label == "Band B"


def test_resolve_desired_bundle_tariff_when_ha_scheduler_off():
    schedule = TariffScheduleConfig(hours=[2] * 24, bands=[TariffBandConfig() for _ in range(4)])
    schedule.bands[2] = TariffBandConfig(work_mode="Peak Shaving")
    tariff = TariffConfig(apply_band_inverter_control=True, schedule=schedule)
    plant = SimpleNamespace(
        control_active=True,
        override=SimpleNamespace(active=False, periods=[]),
        plant_schedule=SimpleNamespace(enabled=False, segments=[]),
        tariff=tariff,
        entity_map={},
        virtual_soc=SimpleNamespace(max_soc=None),
        storm_prep=SimpleNamespace(target_max_soc=100),
        smart_charge=SimpleNamespace(target_max_soc=None, max_target_soc=100),
        forecast_prep=SimpleNamespace(target_max_soc=100),
        outage_prep=SimpleNamespace(target_max_soc=100),
    )
    coordinator = SimpleNamespace(plant=plant, hass=MagicMock())

    bundle = resolve_desired_bundle(coordinator)
    assert bundle is not None
    assert bundle.source == SOURCE_TARIFF
    assert bundle.work_mode == "Peak Shaving"
    assert bundle.label == "Band C"
