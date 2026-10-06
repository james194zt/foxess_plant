"""Performance day totals survive a restart; a day that ended while HA was down still reaches the ledger."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from homeassistant.util import dt as dt_util

from custom_components.foxess_plant.performance.backfill import _needs_backfill
from custom_components.foxess_plant.performance.store import PerformanceStore
from custom_components.foxess_plant.performance.tick import (
    _async_restore_day_state,
    new_daily_accumulator,
    today_net_savings_gbp,
)


def _coordinator(store: PerformanceStore) -> SimpleNamespace:
    return SimpleNamespace(
        _performance_store=store,
        _performance_day="",
        _performance_daily={},
        plant=SimpleNamespace(performance=SimpleNamespace(inverter_ac_limit_kw=5.0)),
    )


def _acc() -> dict:
    return {
        **new_daily_accumulator(),
        "export_earnings_gbp": 0.5,
        "avoided_grid_cost_gbp": 1.25,
        "counters": {"import": 1.0, "export": 2.0, "load": 6.0},
    }


@pytest.mark.asyncio
async def test_store_starts_in_the_config_folder(tmp_path) -> None:
    # HA's config.path returns a str; building the path with "/" crashed every start, so Performance never ran
    import os

    from custom_components.foxess_plant.performance.tick import async_init_performance_store, performance_db_path

    hass = SimpleNamespace(config=SimpleNamespace(path=lambda *p: os.path.join(str(tmp_path), *p)))
    assert performance_db_path(hass, "abc") == os.path.join(str(tmp_path), "foxess_plant", "performance_abc.db")
    coordinator = SimpleNamespace(
        hass=hass,
        config_entry=SimpleNamespace(entry_id="abc"),
        plant=SimpleNamespace(
            performance=SimpleNamespace(
                enabled=True, system_install_cost_gbp=9327.0, system_rte=0.85, inverter_ac_limit_kw=5.0
            ),
            solcast=SimpleNamespace(installation_date=None),
        ),
        _performance_store=None,
        _performance_day="",
        _performance_daily={},
    )
    await async_init_performance_store(coordinator)  # the recorder backfill fails on this fake hass: logged only
    assert coordinator._performance_store is not None
    assert (tmp_path / "foxess_plant" / "performance_abc.db").exists()


def test_hourly_backfilled_days_are_refilled_at_five_minutes() -> None:
    start = dt_util.start_of_local_day() - timedelta(days=2)
    assert _needs_backfill(24, start, dt_util.now())  # a whole past day with only hourly rows
    assert not _needs_backfill(250, start, dt_util.now())  # most of the 288 five-minute slots
    today = dt_util.start_of_local_day()
    assert not _needs_backfill(5, today, today + timedelta(minutes=30))  # just after midnight: few expected


@pytest.mark.asyncio
async def test_restart_carries_on_with_todays_totals(tmp_path) -> None:
    store = PerformanceStore(tmp_path / "perf.db")
    store.init_schema()
    today = dt_util.as_local(dt_util.now()).date().isoformat()
    store.save_day_state(today, _acc())
    coordinator = _coordinator(store)
    await _async_restore_day_state(coordinator, store)
    assert coordinator._performance_day == today
    assert coordinator._performance_daily["counters"] == {"import": 1.0, "export": 2.0, "load": 6.0}
    assert today_net_savings_gbp(coordinator) == 1.75


@pytest.mark.asyncio
async def test_day_that_ended_while_down_is_written_to_the_ledger(tmp_path) -> None:
    store = PerformanceStore(tmp_path / "perf.db")
    store.init_schema()
    yesterday = (dt_util.as_local(dt_util.now()) - timedelta(days=1)).date().isoformat()
    store.save_day_state(yesterday, _acc())
    coordinator = _coordinator(store)
    await _async_restore_day_state(coordinator, store)
    row = store.get_daily_ledger(yesterday)
    assert row is not None and row["net_daily_savings_gbp"] == 1.75
    assert coordinator._performance_day == ""  # today starts fresh
    assert coordinator._performance_daily.get("counters") is None
