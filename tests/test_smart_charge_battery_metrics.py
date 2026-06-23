"""Unit tests for SmartCharge battery metric resolution."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "foxess_plant" / "smart_charge"


def _load(name: str, rel: str):
    path = PKG / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bm = _load("sc_battery_metrics_test", "battery_metrics.py")


class BatteryMetricsTests(unittest.TestCase):
    def test_evo_nominal_and_soc_derive_remaining(self) -> None:
        values = {
            "battery_soc": 80.0,
            "bms_kwh_remaining_1": 10.24,
        }

        def read_float(key: str):
            return values.get(key)

        soc, capacity, remaining = bm.resolve_battery_metrics(
            read_float=read_float,
            read_unit=lambda _key: "kWh",
        )
        self.assertEqual(soc, 80.0)
        self.assertAlmostEqual(capacity, 10.24, places=2)
        self.assertAlmostEqual(remaining, 8.192, places=2)

    def test_derive_capacity_from_remaining_and_soc(self) -> None:
        values = {
            "battery_soc": 80.0,
            "battery_kwh_remaining": 8.0,
        }

        def read_float(key: str):
            return values.get(key)

        _soc, capacity, remaining = bm.resolve_battery_metrics(
            read_float=read_float,
            read_unit=lambda _key: "",
        )
        self.assertAlmostEqual(capacity, 10.0, places=2)
        self.assertAlmostEqual(remaining, 8.0, places=2)

    def test_parse_percent_state(self) -> None:
        self.assertEqual(bm.parse_state_float("87%"), 87.0)


if __name__ == "__main__":
    unittest.main()
