"""Unit tests for SmartCharge spread math (no Home Assistant required)."""

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


spread_math = _load_module("sc_spread_math_test", "smart_charge/spread_math.py")


class SpreadProfitTests(unittest.TestCase):
    def test_spread_profit_positive_import(self) -> None:
        profit = spread_math.spread_profit_per_kwh(
            import_p_per_kwh=5.0,
            export_p_per_kwh=20.0,
            round_trip_efficiency=0.9,
        )
        self.assertAlmostEqual(profit, 15.0)

    def test_spread_profit_negative_import(self) -> None:
        profit = spread_math.spread_profit_per_kwh(
            import_p_per_kwh=-3.0,
            export_p_per_kwh=18.0,
            round_trip_efficiency=0.9,
        )
        self.assertAlmostEqual(profit, 20.7, places=1)


class SpreadPairingTests(unittest.TestCase):
    def test_pair_spread_indices_greedy_non_overlap(self) -> None:
        charge_scores = [(0, 2.0), (1, 4.0), (2, 6.0)]
        export_scores = [(1, 20.0, 5.0), (2, 25.0, 12.0), (3, 30.0, 20.0)]
        pairs = spread_math.pair_spread_indices(charge_scores, export_scores, min_profit_p=3.0)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0], (0, 3, 20.0))

    def test_mode_spread_threshold_green_higher(self) -> None:
        green = spread_math.mode_spread_threshold(
            spread_math.OPERATING_MODE_MAX_GREEN,
            min_spread_profit=3.0,
            green_export_spread_multiplier=2.0,
        )
        profit = spread_math.mode_spread_threshold(
            spread_math.OPERATING_MODE_MAX_PROFIT,
            min_spread_profit=3.0,
            green_export_spread_multiplier=2.0,
        )
        self.assertEqual(green, 6.0)
        self.assertEqual(profit, 3.0)


class WinterFillTests(unittest.TestCase):
    def test_winter_fill_slot_count(self) -> None:
        count = spread_math.winter_fill_slot_count(
            grid_gap_kwh=10.0,
            forecast_kwh=2.0,
            solar_margin=1.15,
            slot_kwh=0.5,
        )
        self.assertGreaterEqual(count, 1)

    def test_winter_fill_zero_when_solar_covers(self) -> None:
        count = spread_math.winter_fill_slot_count(
            grid_gap_kwh=5.0,
            forecast_kwh=20.0,
            solar_margin=1.15,
        )
        self.assertEqual(count, 0)


class PriceDropTests(unittest.TestCase):
    def test_material_import_price_drop(self) -> None:
        prev = [("2026-05-28T00:00:00Z", 10.0), ("2026-05-28T00:30:00Z", 8.0)]
        current = [("2026-05-28T00:00:00Z", 10.0), ("2026-05-28T00:30:00Z", 5.0)]
        self.assertTrue(
            spread_math.material_import_price_drop(prev, current, threshold_p=2.0)
        )
        self.assertFalse(
            spread_math.material_import_price_drop(prev, current, threshold_p=5.0)
        )


if __name__ == "__main__":
    unittest.main()
