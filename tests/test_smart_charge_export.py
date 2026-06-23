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
export_peak = _load_module("sc_export_limits_test", "smart_charge/export_limits.py")


class ExportModeTests(unittest.TestCase):
    def test_mode_limits_profit_vs_safety(self) -> None:
        cfg = SimpleNamespace(
            min_export_p_profit=10.0,
            min_export_p_safety=18.0,
            min_export_p_green=22.0,
            exportable_fraction_profit=1.0,
            exportable_fraction_safety=0.4,
            exportable_fraction_green=0.1,
        )
        profit = export_peak.mode_export_limits(reserve.OPERATING_MODE_MAX_PROFIT, cfg)
        safety = export_peak.mode_export_limits(reserve.OPERATING_MODE_MAX_SAFETY, cfg)
        self.assertEqual(profit, (10.0, 1.0))
        self.assertEqual(safety, (18.0, 0.4))

    def test_green_export_disabled_by_default(self) -> None:
        cfg = SimpleNamespace(export_enabled=True, export_enabled_green=False)
        self.assertFalse(export_peak.export_allowed_for_mode(reserve.OPERATING_MODE_MAX_GREEN, cfg))


if __name__ == "__main__":
    unittest.main()
