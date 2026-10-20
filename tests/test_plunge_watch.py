"""Rate check: while grid charging (any price), re-ask Octopus every 5 minutes; if it contradicts the price the
plan used, take Octopus's rate and re-plan (which stops a charge that isn't worth it at the real price)."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from homeassistant.util import dt as dt_util

from custom_components.foxess_plant import octopus_api
from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator


def _slot_rows(price: float) -> list[dict]:
    now = dt_util.utcnow()
    start = now.replace(minute=0 if now.minute < 30 else 30, second=0, microsecond=0)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return [
        {
            "value_exc_vat": round(price / 1.05, 4),
            "value_inc_vat": price,
            "valid_from": start.strftime(fmt),
            "valid_to": (start + timedelta(minutes=30)).strftime(fmt),
        }
    ]


class FakePlant:
    def __init__(self, hass, cached_price: float, api_rows: list[dict] | Exception) -> None:
        self.hass = hass
        dyn = SimpleNamespace(
            native_octopus=lambda: True, api_key_configured=lambda: True, api_key="sk_test"
        )
        self.plant = SimpleNamespace(
            tariff=SimpleNamespace(dynamic=dyn), smart_charge=SimpleNamespace(meter_rate_tolerance_p_per_kwh=0.5)
        )
        self._octopus_cache = {
            "import_product_code": "AGILE-24-10-01",
            "import_tariff_code": "E-1R-AGILE-24-10-01-C",
            "import_meter": {"mpan": "1900000000000"},
            "import_rates": _slot_rows(cached_price),
        }
        self._smart_charge_decision = {"action": "arbitrage"}
        self.api_rows = api_rows
        self.noted_rates, self.actions, self.replans = [], [], 0

    def _octopus_native_active(self):
        return True

    def _octopus_rate_limited(self):
        return False

    def _note_octopus_rate_limit(self, *messages):
        pass

    def _sync_octopus_current_rates_from_cache(self):
        pass

    async def _async_note_plunge_rates(self, rows, meta, *, track_all=False):
        self.noted_rates.append((rows, meta, track_all))

    async def _async_note_plunge_action(self, window, what, *, details=None):
        self.actions.append(what)

    async def _evaluate_smart_charge(self):
        self.replans += 1

    async def async_request_refresh(self):
        pass

    _grid_charging_now = FoxessPlantCoordinator._grid_charging_now


@pytest.fixture
def fake_api(monkeypatch):
    def install(plant: FakePlant):
        async def get_unit_rates(self, product, tariff, **kwargs):
            if isinstance(plant.api_rows, Exception):
                raise plant.api_rows
            self.rates_meta[tariff] = {"url": "https://api.octopus.energy/v1/…", "server_date": "Mon, 20 Oct 2026"}
            return plant.api_rows

        monkeypatch.setattr(octopus_api.OctopusApiClient, "get_unit_rates", get_unit_rates)

    return install


@pytest.mark.asyncio
async def test_still_negative_keeps_charging_and_is_recorded(hass, fake_api) -> None:
    plant = FakePlant(hass, -2.0, _slot_rows(-2.0))
    fake_api(plant)
    await FoxessPlantCoordinator._async_plunge_watch(plant)
    assert plant.replans == 0
    rows, meta, track_all = plant.noted_rates[0]
    assert meta["purpose"].startswith("rate check") and track_all


@pytest.mark.asyncio
async def test_not_negative_any_more_replans_to_stop_the_charge(hass, fake_api) -> None:
    plant = FakePlant(hass, -2.0, _slot_rows(15.3))
    fake_api(plant)
    await FoxessPlantCoordinator._async_plunge_watch(plant)
    assert plant.replans == 1
    assert plant._octopus_cache["import_rates"][0]["value_inc_vat"] == 15.3  # planner now sees the real price
    assert any("15.30p" in a and "-2.00p" in a for a in plant.actions)


@pytest.mark.asyncio
async def test_ordinary_cheap_charge_contradicted_by_the_api_replans(hass, fake_api) -> None:
    # We think it's 6p and charge; Octopus says 20p
    plant = FakePlant(hass, 6.0, _slot_rows(20.0))
    fake_api(plant)
    await FoxessPlantCoordinator._async_plunge_watch(plant)
    assert plant.replans == 1
    assert plant._octopus_cache["import_rates"][0]["value_inc_vat"] == 20.0


@pytest.mark.asyncio
async def test_api_agrees_within_tolerance_keeps_the_charge(hass, fake_api) -> None:
    plant = FakePlant(hass, 6.0, _slot_rows(6.3))
    fake_api(plant)
    await FoxessPlantCoordinator._async_plunge_watch(plant)
    assert plant.replans == 0
    assert plant._octopus_cache["import_rates"][0]["value_inc_vat"] == 6.0


@pytest.mark.asyncio
async def test_octopus_no_longer_lists_the_half_hour_stops_too(hass, fake_api) -> None:
    plant = FakePlant(hass, -2.0, [])
    fake_api(plant)
    await FoxessPlantCoordinator._async_plunge_watch(plant)
    assert plant.replans == 1
    assert plant._octopus_cache["import_rates"] == []  # unpublished price: never scheduled


@pytest.mark.asyncio
async def test_failed_request_is_logged_and_the_charge_carries_on(hass, fake_api) -> None:
    plant = FakePlant(hass, -2.0, octopus_api.OctopusApiError("Octopus network error"))
    fake_api(plant)
    await FoxessPlantCoordinator._async_plunge_watch(plant)
    assert plant.replans == 0
    assert "didn't answer" in plant.actions[0]


@pytest.mark.asyncio
async def test_does_nothing_when_not_grid_charging(hass, fake_api) -> None:
    plant = FakePlant(hass, -2.0, _slot_rows(20.0))
    plant._smart_charge_decision = {"action": "idle"}
    fake_api(plant)
    await FoxessPlantCoordinator._async_plunge_watch(plant)
    assert plant.noted_rates == [] and plant.replans == 0
