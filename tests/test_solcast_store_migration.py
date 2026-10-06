"""A version 1 Solcast store file loads (and is upgraded) instead of failing every start."""

import pytest

from custom_components.foxess_plant.solcast_store import STORAGE_VERSION, SolcastForecastStore

KEY = "foxess_plant.solcast_forecasts.entry1"


@pytest.mark.asyncio
async def test_version_1_file_loads_and_is_saved_as_version_2(hass, hass_storage) -> None:
    hass_storage[KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": KEY,
        "data": {"current": {"a": 1}, "history": [{"x": 1}]},
    }
    data = await SolcastForecastStore(hass, "entry1").async_load()
    assert data["current"] == {"a": 1}
    assert data["history"] == [{"x": 1}]
    assert data["daily_intraday"] == {}
    await hass.async_block_till_done()
    assert hass_storage[KEY]["version"] == STORAGE_VERSION  # upgraded on disk, so the next start is clean
