"""Saving the PV configuration only asks Solcast for a new forecast when what it's asked for changes.

The Solar Forecast page's Save sends the Solcast settings (which fetch) and then the PV config: each save used two
of the 10 daily hobbyist requests (seen in the request log on 14 Oct 2026).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator
from custom_components.foxess_plant.models import PlantConfig, PvSystemConfig

PV = {
    "pv1": {"enabled": True, "panel_count": 10, "panel_watts": 450, "tilt": 45, "azimuth": 164, "efficiency_factor": 99},
    "pv2": {"enabled": False},
}


class _Fake:
    def __init__(self):
        self.config_entry = SimpleNamespace(data={})
        self.plant = SimpleNamespace(pv_config=PvSystemConfig.from_dict(PV), solcast=SimpleNamespace(installation_date=None))
        self.hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_update_entry=lambda entry, data: setattr(entry, "data", data))
        )
        self.fetches = 0

    def update_plant_config(self, plant):
        self.plant.pv_config = plant.pv_config

    def _solcast_pv_active(self):
        return True

    async def _async_refresh_solcast_pv(self, *, force=False):
        self.fetches += 1

    async def async_request_refresh(self):
        pass


class _SolcastFake:
    """Just what the Solcast save's 'is a forecast needed?' check reads."""

    def __init__(self, *, fresh=True, covers=True):
        self.plant = SimpleNamespace(
            pv_config=PvSystemConfig.from_dict(PV),
            solcast=SimpleNamespace(api_key="key-a", rooftop_site_bindings={"pv1": "site-1"}),
        )
        self.fresh, self.covers = fresh, covers

    def _solcast_fresh(self):
        return self.fresh

    def _solcast_forecast_covers_now(self):
        return self.covers

    def _solcast_forecast_inputs(self):
        return FoxessPlantCoordinator._solcast_forecast_inputs(self)


def _needs(fake, before) -> bool:
    return FoxessPlantCoordinator._solcast_save_needs_forecast(fake, before)


def test_a_solcast_save_only_fetches_when_a_forecast_is_missing_or_its_inputs_changed() -> None:
    fake = _SolcastFake()
    before = fake._solcast_forecast_inputs()
    assert not _needs(fake, before)  # save + free site check only; the schedule carries on
    fake.plant.solcast.api_key = "key-b"
    assert _needs(fake, before)  # another account
    fake.plant.solcast.api_key = "key-a"
    fake.plant.solcast.rooftop_site_bindings = {"pv1": "site-2"}
    assert _needs(fake, before)  # matched to a different site
    fake.plant.solcast.rooftop_site_bindings = {"pv1": "site-1"}
    fake.plant.pv_config = PvSystemConfig.from_dict({**PV, "pv1": {**PV["pv1"], "tilt": 30}})
    assert _needs(fake, before)  # the rooftop request changed
    assert _needs(_SolcastFake(fresh=False), before)  # last good forecast over a day old (e.g. re-enabled)
    assert _needs(_SolcastFake(covers=False), before)  # forecast ran out


@pytest.mark.asyncio
async def test_unchanged_pv_config_costs_no_request(monkeypatch) -> None:
    monkeypatch.setattr(PlantConfig, "from_entry_data", staticmethod(lambda data: SimpleNamespace(pv_config=PvSystemConfig.from_dict(data["pv_config"]))))
    fake = _Fake()
    await FoxessPlantCoordinator.async_save_pv_config(fake, pv_config=PV)
    assert fake.fetches == 0
    tilted = {**PV, "pv1": {**PV["pv1"], "tilt": 30}}
    await FoxessPlantCoordinator.async_save_pv_config(fake, pv_config=tilted)
    assert fake.fetches == 1
