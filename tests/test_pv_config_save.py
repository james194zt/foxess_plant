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


@pytest.mark.asyncio
async def test_unchanged_pv_config_costs_no_request(monkeypatch) -> None:
    monkeypatch.setattr(PlantConfig, "from_entry_data", staticmethod(lambda data: SimpleNamespace(pv_config=PvSystemConfig.from_dict(data["pv_config"]))))
    fake = _Fake()
    await FoxessPlantCoordinator.async_save_pv_config(fake, pv_config=PV)
    assert fake.fetches == 0
    tilted = {**PV, "pv1": {**PV["pv1"], "tilt": 30}}
    await FoxessPlantCoordinator.async_save_pv_config(fake, pv_config=tilted)
    assert fake.fetches == 1
