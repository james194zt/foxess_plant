"""SmartCharge settings reach the planner as entered: a real 0 isn't swapped for the default, the site
postcode keeps only the area, and Prefer Greener Charging gets a carbon forecast on any supplier."""

import dataclasses
from datetime import timedelta
from types import SimpleNamespace

import pytest
from homeassistant.util import dt as dt_util

from custom_components.foxess_plant import carbon_intensity_neso
from custom_components.foxess_plant.coordinator import FoxessPlantCoordinator
from custom_components.foxess_plant.models import PlantConfig, PvSystemConfig, SmartChargeConfig

# Fields where 0 isn't a valid setting (the save schema's minimum is above 0, or it's clamped up on purpose)
CLAMPED_ABOVE_ZERO = {"max_charge_kw", "load_history_days", "max_target_soc"}


def _numeric_fields():
    for f in dataclasses.fields(SmartChargeConfig):
        if f.type in ("float", "int") and f.name not in CLAMPED_ABOVE_ZERO:
            yield f.name


@pytest.mark.parametrize("name", list(_numeric_fields()))
def test_zero_is_kept(name):
    """`x or default` turned 0 into the default (Outage Hours 0 -> 3, Carbon Weight 0 -> 0.5, min export 0p -> 12p)."""
    cfg = SmartChargeConfig.from_dict({name: 0}, [])
    assert getattr(cfg, name) == 0
    assert SmartChargeConfig.from_dict(cfg.to_dict(), []).to_dict()[name] == 0


def test_missing_and_blank_still_use_defaults():
    cfg = SmartChargeConfig.from_dict({"outage_reserve_hours": "", "green_carbon_weight": None}, [])
    assert cfg.outage_reserve_hours == 3.0
    assert cfg.green_carbon_weight == 0.5


@pytest.mark.parametrize(
    ("typed", "stored"),
    [("SW1A 1AA", "SW1A"), ("sw1a1aa", "SW1A"), ("M1 1AE", "M1"), ("sw1a", "SW1A"), (" ", None), (None, None)],
)
def test_postcode_area_keeps_only_the_area(typed, stored):
    assert PvSystemConfig.from_dict({"postcode_area": typed}).postcode_area == stored
    assert PvSystemConfig.from_dict({"postcode_area": typed}).to_dict()["postcode_area"] == stored


def test_old_max_green_becomes_max_profit_with_the_tick_box():
    cfg = SmartChargeConfig.from_dict({"operating_mode": "max_green"}, [])
    assert cfg.operating_mode == "max_profit" and cfg.prefer_greener_charging is True
    # Once saved, the tick-box is stored on its own and wins
    cfg = SmartChargeConfig.from_dict({"operating_mode": "max_safety", "prefer_greener_charging": False}, [])
    assert cfg.operating_mode == "max_safety" and cfg.prefer_greener_charging is False
    assert SmartChargeConfig.from_dict({}, []).prefer_greener_charging is False


def test_0_9_538_carbon_postcode_moves_to_pv_config():
    data = {"device_id": "d", "inverter_target": "EVO-10", "smart_charge": {"carbon_postcode": "ST4"}, "pv_config": {}}
    assert PlantConfig.from_entry_data(data).pv_config.postcode_area == "ST4"
    data["pv_config"] = {"postcode_area": "M1"}  # the PV config's own value wins
    assert PlantConfig.from_entry_data(data).pv_config.postcode_area == "M1"


def _fake(prefer=True, octopus=None, postcode=None):
    fake = SimpleNamespace(
        hass=None,
        plant=SimpleNamespace(
            smart_charge=SimpleNamespace(prefer_greener_charging=prefer),
            pv_config=SimpleNamespace(postcode_area=postcode),
        ),
        _octopus_greener_cache={"carbon_periods": octopus or []},
        _neso_carbon=[],
        _neso_carbon_tried_at=None,
        _neso_carbon_fetched_at=None,
        _neso_carbon_error=None,
        _neso_carbon_postcode=None,
    )
    fake._smart_charge_greener_inputs = lambda: FoxessPlantCoordinator._smart_charge_greener_inputs(fake)
    return fake


def _rows(n=96, score=10):
    start = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    out = []
    for i in range(n):
        s = int((start + timedelta(minutes=30 * i)).timestamp() * 1000)
        out.append({"start_ms": s, "end_ms": s + 1_800_000, "gco2_per_kwh": 100.0, "low_carbon_score": score,
                    "source": "neso-national"})
    return out


@pytest.fixture
def neso(monkeypatch):
    calls = []
    answer = {"rows": _rows()}

    async def fetch(hass, postcode, *, hours=48):
        calls.append(postcode)
        if isinstance(answer["rows"], Exception):
            raise answer["rows"]
        return answer["rows"]

    monkeypatch.setattr(carbon_intensity_neso, "fetch_neso_regional_carbon", fetch)
    return SimpleNamespace(calls=calls, answer=answer)


@pytest.mark.asyncio
async def test_greener_charging_without_octopus_uses_national_forecast(neso):
    fake = _fake()
    periods = await FoxessPlantCoordinator._async_smart_charge_carbon_periods(fake)
    assert len(periods) >= 90 and neso.calls == [""]  # "" = national
    status = FoxessPlantCoordinator._smart_charge_carbon_status(fake)
    assert status["source"] == "neso_national" and status["until"] and status["error"] is None
    # Within the hour: cached, not asked again
    await FoxessPlantCoordinator._async_smart_charge_carbon_periods(fake)
    assert neso.calls == [""]


@pytest.mark.asyncio
async def test_without_the_tick_box_never_asks(neso):
    assert await FoxessPlantCoordinator._async_smart_charge_carbon_periods(_fake(prefer=False)) == []
    assert neso.calls == []


@pytest.mark.asyncio
async def test_octopus_carbon_wins_when_it_covers_the_day(neso):
    octopus = _rows(score=3)
    periods = await FoxessPlantCoordinator._async_smart_charge_carbon_periods(_fake(octopus=octopus))
    assert periods == octopus and neso.calls == []


@pytest.mark.asyncio
async def test_failed_fetch_is_reported_and_not_retried_within_the_hour(neso):
    neso.answer["rows"] = RuntimeError("timeout")
    fake = _fake()
    assert await FoxessPlantCoordinator._async_smart_charge_carbon_periods(fake) == []
    status = FoxessPlantCoordinator._smart_charge_carbon_status(fake)
    assert status["source"] is None and status["tried"] and status["error"]
    await FoxessPlantCoordinator._async_smart_charge_carbon_periods(fake)
    assert len(neso.calls) == 1


@pytest.mark.asyncio
async def test_postcode_change_refetches_regionally(neso):
    fake = _fake()
    await FoxessPlantCoordinator._async_smart_charge_carbon_periods(fake)
    fake.plant.pv_config.postcode_area = "SW1A"
    await FoxessPlantCoordinator._async_smart_charge_carbon_periods(fake)
    assert neso.calls == ["", "SW1A"]
