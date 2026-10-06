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

    def test_accepts_statistics_start_mean_rows(self):
        # Recorder stats from _fetch_statistics_points use start/mean, not t/v.
        pts = [{"start": 0, "mean": 2.0}, {"start": 3600, "mean": 2.0}]
        self.assertAlmostEqual(sca.integrate_power_kwh(pts, 0, 3_600_000), 2.0, places=3)

    def test_stats_rows_to_power_points(self):
        rows = [{"start": 1_700_000_000, "mean": 1.5}, {"start": 1_700_000_300, "mean": 2.0}]
        pts = sca.stats_rows_to_power_points(rows)
        self.assertEqual(len(pts), 2)
        self.assertIn("t", pts[0])
        self.assertIn("v", pts[0])
        self.assertEqual(pts[0]["v"], 1.5)


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


class TestPowerSeries(unittest.TestCase):
    def test_unit_scale(self):
        self.assertEqual(sca.power_unit_scale("W"), 0.001)
        self.assertEqual(sca.power_unit_scale("kW"), 1.0)
        self.assertEqual(sca.power_unit_scale(None), 1.0)

    def test_merge_prefers_five_minute_and_scales(self):
        hourly = [{"t": 0.0, "v": 1000.0}, {"t": 3_600_000.0, "v": 2000.0}, {"t": 7_200_000.0, "v": 9999.0}]
        fine = [{"t": 7_200_000.0, "v": 3000.0}, {"t": 7_500_000.0, "v": 3000.0}]
        merged = sca.merge_power_series(hourly, fine, scale=0.001)
        self.assertEqual([p["t"] for p in merged], [0.0, 3_600_000.0, 7_200_000.0, 7_500_000.0])
        self.assertEqual([p["v"] for p in merged], [1.0, 2.0, 3.0, 3.0])


class TestHowUsed(unittest.TestCase):
    @staticmethod
    def _ms(y, mo, d, h) -> float:
        return datetime(y, mo, d, h, tzinfo=timezone.utc).timestamp() * 1000

    def test_charged_vs_skipped_status(self):
        s_a, e_a = self._ms(2026, 10, 5, 2), self._ms(2026, 10, 5, 3)
        s_b, e_b = self._ms(2026, 10, 6, 2), self._ms(2026, 10, 6, 3)
        planned = [
            {"start_ms": s_a, "end_ms": e_a, "action": "charge", "planned_import_kwh": 1.8, "import_p_per_kwh": 8.0},
            {"start_ms": s_b, "end_ms": e_b, "action": "charge", "planned_import_kwh": 1.8, "import_p_per_kwh": 8.0},
        ]
        # battery charged during slot A (1.8 kW for the hour), nothing during slot B
        batt_charge = [{"t": s_a, "v": 1.8}, {"t": e_a, "v": 1.8}, {"t": s_b, "v": 0.0}, {"t": e_b, "v": 0.0}]
        econ = {
            "2026-10-05": {
                "reason": "Off-peak charge", "saving_p": 12.0, "operating_mode": "price_arbitrage",
                "planned_grid_charge_kwh": 1.8,
            },
            "2026-10-06": {
                "reason": "Self use — no grid charge needed", "saving_p": 0.0, "operating_mode": "max_safety",
                "planned_grid_charge_kwh": 1.8,
            },
        }
        rows = sca.build_how_used(
            daily_economics=econ,
            planned_slots=planned,
            battery_charge_pts=batt_charge,
            grid_export_pts=[],
            range_start_ms=self._ms(2026, 10, 5, 0),
            range_end_ms=self._ms(2026, 10, 6, 23),
        )
        by_date = {r["date"]: r for r in rows}
        self.assertEqual(by_date["2026-10-05"]["status"], "charged")
        self.assertAlmostEqual(by_date["2026-10-05"]["actual_charge_kwh"], 1.8, places=1)
        self.assertEqual(by_date["2026-10-05"]["saving_p"], 12.0)
        self.assertEqual(by_date["2026-10-06"]["status"], "skipped")
        self.assertAlmostEqual(by_date["2026-10-06"]["actual_charge_kwh"], 0.0, places=2)
        summary = sca._how_used_summary(rows)
        self.assertEqual(summary["nights_charged"], 1)
        self.assertEqual(summary["nights_skipped_solar"], 1)
        self.assertEqual(summary["estimated_saving_p"], 12.0)


if __name__ == "__main__":
    unittest.main()
