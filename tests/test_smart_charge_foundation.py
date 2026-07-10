"""Unit tests for SmartCharge Phase 1 foundation (no Home Assistant required)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = REPO_ROOT / "custom_components" / "foxess_plant"


def _load_module(name: str, relative: str):
    path = PKG_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


reserve = _load_module("sc_reserve_test", "smart_charge/reserve.py")
guards = _load_module("sc_guards_test", "smart_charge/guards.py")


class ReserveTests(unittest.TestCase):
    def test_outage_reserve_baseline(self) -> None:
        reserve_kwh = reserve.compute_outage_reserve_kwh(
            avg_home_load_kw=2.0,
            vulnerable_hours=3.0,
            safety_margin=1.2,
            operating_mode=reserve.OPERATING_MODE_MAX_SAFETY,
            safety_reserve_multiplier=1.5,
        )
        self.assertAlmostEqual(reserve_kwh, 2.0 * 3.0 * 1.2 * 1.5)

    def test_exportable_kwh_respects_floor(self) -> None:
        self.assertAlmostEqual(reserve.compute_exportable_kwh(kwh_remaining=10.0, reserve_kwh=4.0), 6.0)
        self.assertAlmostEqual(reserve.compute_exportable_kwh(kwh_remaining=2.0, reserve_kwh=4.0), 0.0)
        self.assertIsNone(reserve.compute_exportable_kwh(kwh_remaining=None, reserve_kwh=4.0))

    def test_mode_reserve_multiplier_safety(self) -> None:
        mult = reserve.mode_reserve_multiplier(
            reserve.OPERATING_MODE_MAX_SAFETY,
            safety_reserve_multiplier=1.5,
        )
        self.assertEqual(mult, 1.5)


class GuardTests(unittest.TestCase):
    def test_inactive_when_disabled(self) -> None:
        reason = guards.smart_charge_evaluation_blocked(
            enabled=False,
            control_active=True,
            outage_prep_enabled=False,
            active_outage_triggers=[],
            storm_prep_enabled=False,
            active_storm_triggers=[],
        )
        self.assertEqual(reason, "inactive")

    def test_outage_blocks_before_storm(self) -> None:
        reason = guards.smart_charge_evaluation_blocked(
            enabled=True,
            control_active=True,
            outage_prep_enabled=True,
            active_outage_triggers=["grid_down"],
            storm_prep_enabled=True,
            active_storm_triggers=["wind"],
        )
        self.assertEqual(reason, "outage")

    def test_storm_blocks_when_no_outage(self) -> None:
        reason = guards.smart_charge_evaluation_blocked(
            enabled=True,
            control_active=True,
            outage_prep_enabled=True,
            active_outage_triggers=[],
            storm_prep_enabled=True,
            active_storm_triggers=["wind"],
        )
        self.assertEqual(reason, "storm")

    def test_clear_when_enabled(self) -> None:
        reason = guards.smart_charge_evaluation_blocked(
            enabled=True,
            control_active=True,
            outage_prep_enabled=True,
            active_outage_triggers=[],
            storm_prep_enabled=True,
            active_storm_triggers=[],
        )
        self.assertIsNone(reason)


class HouseEnergyBudgetTests(unittest.TestCase):
    """Pure formula checks for Solcast house-load budget (no HA import)."""

    def test_grid_gap_and_target_kwh(self) -> None:
        load_kw = 2.0
        dark_hours = 5.0
        margin = 1.15
        reserve_kwh = 7.2
        forecast_kwh = 4.0
        capacity_kwh = 10.0
        max_target_soc = 95.0

        dark_hours_kwh = load_kw * dark_hours
        pv_cover_kwh = forecast_kwh / margin
        grid_gap_kwh = max(0.0, dark_hours_kwh - pv_cover_kwh)
        target_kwh = reserve_kwh + grid_gap_kwh
        target_soc_pct = min(max_target_soc, target_kwh / capacity_kwh * 100.0)

        self.assertAlmostEqual(dark_hours_kwh, 10.0)
        self.assertAlmostEqual(pv_cover_kwh, 4.0 / 1.15, places=2)
        self.assertAlmostEqual(grid_gap_kwh, 10.0 - 4.0 / 1.15, places=2)
        self.assertAlmostEqual(target_kwh, reserve_kwh + grid_gap_kwh, places=2)
        self.assertLessEqual(target_soc_pct, max_target_soc)


class AgilePollBoundaryTests(unittest.TestCase):
    """15-minute Agile poll alignment (mirrors octopus_tariff.next_agile_poll_boundary)."""

    @staticmethod
    def _next_boundary_local(local_dt, *, interval_minutes: int = 15):
        from datetime import timedelta

        step = max(1, min(60, interval_minutes))
        minute = local_dt.minute
        next_minute = ((minute // step) + 1) * step
        if next_minute >= 60:
            return local_dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return local_dt.replace(minute=next_minute, second=0, microsecond=0)

    def test_aligns_to_next_quarter_hour(self) -> None:
        from datetime import datetime

        when = datetime(2026, 7, 10, 14, 7, 30)
        nxt = self._next_boundary_local(when)
        self.assertEqual((nxt.hour, nxt.minute), (14, 15))

    def test_rolls_hour_at_top_of_hour(self) -> None:
        from datetime import datetime

        when = datetime(2026, 7, 10, 14, 45, 0)
        nxt = self._next_boundary_local(when)
        self.assertEqual((nxt.hour, nxt.minute), (15, 0))


if __name__ == "__main__":
    unittest.main()
