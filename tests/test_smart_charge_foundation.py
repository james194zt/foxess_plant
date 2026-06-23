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


if __name__ == "__main__":
    unittest.main()
