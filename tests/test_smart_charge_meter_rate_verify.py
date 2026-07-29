"""Unit tests for SmartCharge Glow/meter rate verify (no Home Assistant required)."""

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


verify = _load_module("sc_meter_rate_verify_test", "smart_charge/meter_rate_verify.py")


class MeterRateVerifyTests(unittest.TestCase):
    def test_small_pence_not_multiplied_when_near_api(self) -> None:
        # User example: API -0.037p, meter -0.04p (both already pence).
        p = verify.normalize_rate_to_pence(-0.04, api_hint_p=-0.037)
        self.assertAlmostEqual(p, -0.04)

    def test_pounds_converted_when_closer_to_api(self) -> None:
        p = verify.normalize_rate_to_pence(0.152, api_hint_p=15.2)
        self.assertAlmostEqual(p, 15.2)

    def test_agree_within_tolerance(self) -> None:
        result = verify.verify_meter_import_rate(
            enabled=True,
            entity_id="sensor.glow_import_rate",
            api_p_per_kwh=-0.037,
            meter_raw=-0.04,
            tolerance_p=0.5,
        )
        self.assertEqual(result.status, "ok")
        self.assertFalse(result.blocks_arm)

    def test_mismatch_blocks_and_mentions_recheck(self) -> None:
        result = verify.verify_meter_import_rate(
            enabled=True,
            entity_id="sensor.glow_import_rate",
            api_p_per_kwh=-5.0,
            meter_raw=18.0,
            meter_unit="p/kWh",
            tolerance_p=0.5,
            recheck_minutes=5,
        )
        self.assertEqual(result.status, "mismatch")
        self.assertTrue(result.blocks_arm)
        self.assertIn("recheck in 5 min", result.detail)

    def test_unavailable_does_not_block(self) -> None:
        result = verify.verify_meter_import_rate(
            enabled=True,
            entity_id="sensor.glow_import_rate",
            api_p_per_kwh=12.0,
            meter_raw=None,
        )
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(result.blocks_arm)

    def test_disabled_or_no_entity_skips(self) -> None:
        result = verify.verify_meter_import_rate(
            enabled=True,
            entity_id=None,
            api_p_per_kwh=12.0,
            meter_raw=0.12,
        )
        self.assertEqual(result.status, "skipped")
        self.assertFalse(result.blocks_arm)


if __name__ == "__main__":
    unittest.main()
