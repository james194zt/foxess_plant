"""Unit tests for SmartCharge Analysis report helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "foxess_plant"


def _install_ha_stubs() -> None:
    if "homeassistant.util.dt" in sys.modules:
        return
    for name in (
        "homeassistant",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.helpers.entity_registry",
        "homeassistant.util",
        "homeassistant.util.dt",
        "homeassistant.components",
        "homeassistant.components.recorder",
        "homeassistant.components.recorder.util",
    ):
        sys.modules.setdefault(name, types.ModuleType(name))
    dt = sys.modules["homeassistant.util.dt"]
    dt.as_local = lambda value: value
    dt.as_utc = lambda value: value
    dt.utcnow = lambda: datetime.now(timezone.utc)
    dt.utc_from_timestamp = lambda value: datetime.fromtimestamp(value, timezone.utc)
    dt.now = lambda: datetime.now()
    dt.parse_datetime = lambda raw: datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    core = sys.modules["homeassistant.core"]
    core.HomeAssistant = type("HomeAssistant", (), {})


def _load(name: str, rel: str):
    _install_ha_stubs()
    path = PKG / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sca = _load("sca_test", "smart_charge_analysis.py")


class TestIntegratePower(unittest.TestCase):
    def test_constant_power_one_hour(self):
        pts = [{"t": 0, "v": 2.0}, {"t": 3_600_000, "v": 2.0}]
        self.assertAlmostEqual(sca.integrate_power_kwh(pts, 0, 3_600_000), 2.0, places=3)

    def test_clipped_window(self):
        pts = [{"t": 0, "v": 0}, {"t": 3_600_000, "v": 4.0}]
        self.assertAlmostEqual(sca.integrate_power_kwh(pts, 0, 1_800_000), 1.0, places=2)


class TestPairBinary(unittest.TestCase):
    def test_on_off_pair(self):
        states = [
            {"state": "off", "last_changed": "2026-05-28T10:00:00+00:00"},
            {"state": "on", "last_changed": "2026-05-28T11:00:00+00:00"},
            {"state": "off", "last_changed": "2026-05-28T12:00:00+00:00"},
        ]
        periods = sca.pair_binary_on_periods(states, range_end_ms=13 * 3_600_000)
        self.assertEqual(len(periods), 1)
        self.assertGreater(periods[0]["end_ms"], periods[0]["start_ms"])


class TestPlanSlots(unittest.TestCase):
    def test_resolve_overnight_slot(self):
        anchor = datetime(2026, 5, 28, 16, 0, tzinfo=ZoneInfo("Europe/London"))
        bounds = sca.resolve_slot_range_ms(anchor, "23:00", "06:00")
        self.assertIsNotNone(bounds)
        start_ms, end_ms = bounds
        self.assertLess(start_ms, end_ms)
        self.assertGreater(end_ms - start_ms, 6 * 3_600_000)


class TestReportsPeriod(unittest.TestCase):
    def test_week_bounds(self):
        now = datetime(2026, 5, 28, 12, 0, tzinfo=ZoneInfo("Europe/London"))
        start, end, can_next = sca.reports_period_bounds("week", 0, now=now)
        self.assertEqual(start.weekday(), 0)
        self.assertFalse(can_next)


if __name__ == "__main__":
    unittest.main()
