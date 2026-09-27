"""Unit tests for SmartCharge export peak logic (no Home Assistant required)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

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


reserve = _load_module("sc_reserve_test2", "smart_charge/reserve.py")
planner = _load_module("sc_planner_export_test", "smart_charge/planner.py")


class ExportModeTests(unittest.TestCase):
    def _params(self, mode: str, **extra):
        cfg = SimpleNamespace(
            operating_mode=mode,
            min_export_p_profit=10.0,
            min_export_p_safety=18.0,
            min_export_p_green=22.0,
            exportable_fraction_profit=1.0,
            exportable_fraction_safety=0.4,
            exportable_fraction_green=0.1,
            export_min_soc=40.0,
            **extra,
        )
        return planner.params_from_config(cfg, capacity_kwh=10.0, reserve_kwh=1.0)

    def test_mode_limits_profit_vs_safety(self) -> None:
        profit = self._params(reserve.OPERATING_MODE_MAX_PROFIT)
        safety = self._params(reserve.OPERATING_MODE_MAX_SAFETY)
        self.assertEqual(profit.min_export_p, 10.0)
        self.assertEqual(safety.min_export_p, 18.0)
        # Export budget = fraction of the energy above the 40% export floor.
        self.assertAlmostEqual(profit.max_export_kwh, 6.0)
        self.assertAlmostEqual(safety.max_export_kwh, 2.4)

    def test_green_export_disabled_by_default(self) -> None:
        green = self._params(reserve.OPERATING_MODE_MAX_GREEN, export_enabled=True, export_enabled_green=False)
        self.assertFalse(green.export_allowed)


class ExportFloorTests(unittest.TestCase):
    def test_exportable_respects_export_min_soc(self) -> None:
        # 10 kWh remaining on 10 kWh pack at 100% SOC; floor 40% => 4 kWh reserved
        kwh = reserve.compute_exportable_kwh(
            kwh_remaining=10.0,
            reserve_kwh=0.0,
            capacity_kwh=10.0,
            export_min_soc=40.0,
            soc_pct=100.0,
        )
        self.assertAlmostEqual(kwh, 6.0)

    def test_exportable_zero_at_floor(self) -> None:
        kwh = reserve.compute_exportable_kwh(
            kwh_remaining=4.0,
            reserve_kwh=0.0,
            capacity_kwh=10.0,
            export_min_soc=40.0,
            soc_pct=40.0,
        )
        self.assertEqual(kwh, 0.0)
        self.assertTrue(reserve.export_floor_reached(soc_pct=40.0, export_min_soc=40.0))
        self.assertTrue(reserve.export_floor_reached(soc_pct=39.0, export_min_soc=40.0))
        self.assertFalse(reserve.export_floor_reached(soc_pct=41.0, export_min_soc=40.0))

    def test_export_floor_higher_than_outage_reserve(self) -> None:
        # Outage reserve 1 kWh but export floor 50% of 10 kWh => 5 kWh floor
        kwh = reserve.compute_exportable_kwh(
            kwh_remaining=8.0,
            reserve_kwh=1.0,
            capacity_kwh=10.0,
            export_min_soc=50.0,
            soc_pct=80.0,
        )
        self.assertAlmostEqual(kwh, 3.0)


if __name__ == "__main__":
    unittest.main()
