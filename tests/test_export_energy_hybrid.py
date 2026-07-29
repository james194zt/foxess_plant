"""Tests for hybrid export kWh helpers."""

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
PKG_NAME = "custom_components.foxess_plant"
UK_TZ = ZoneInfo("Europe/London")


def _install_ha_stubs() -> None:
    for name in (
        "homeassistant",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.util",
        "homeassistant.util.dt",
    ):
        sys.modules.setdefault(name, types.ModuleType(name))
    dt = sys.modules["homeassistant.util.dt"]
    dt.as_local = lambda value: value
    dt.as_utc = lambda value: value
    dt.utcnow = lambda: datetime.now(timezone.utc)
    dt.now = lambda tz=None: datetime.now(tz or timezone.utc)
    dt.parse_datetime = lambda raw: datetime.fromisoformat(str(raw).replace("Z", "+00:00"))


def _ensure_pkg() -> None:
    sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
    if PKG_NAME not in sys.modules:
        pkg = types.ModuleType(PKG_NAME)
        pkg.__path__ = [str(PKG)]
        sys.modules[PKG_NAME] = pkg


_install_ha_stubs()
_ensure_pkg()
_spec = importlib.util.spec_from_file_location(
    f"{PKG_NAME}.export_energy_hybrid", PKG / "export_energy_hybrid.py"
)
eh = importlib.util.module_from_spec(_spec)
sys.modules[f"{PKG_NAME}.export_energy_hybrid"] = eh
_spec.loader.exec_module(eh)


class TestExportEnergyHybrid(unittest.TestCase):
    def test_cumulative_deltas(self):
        daily_max = {
            "2026-07-26": 250.0,
            "2026-07-27": 270.0,
            "2026-07-28": 275.5,
        }
        rows = eh.daily_kwh_from_cumulative_max(daily_max)
        self.assertEqual(rows[0]["date"], "2026-07-27")
        self.assertEqual(rows[0]["kwh"], 20.0)
        self.assertEqual(rows[1]["kwh"], 5.5)

    def test_today_sensor_uses_day_max(self):
        daily_max = {"2026-07-27": 12.3, "2026-07-28": 0.0, "2026-07-29": 4.1}
        rows = eh.daily_kwh_from_today_sensor_max(daily_max)
        self.assertEqual([r["date"] for r in rows], ["2026-07-27", "2026-07-29"])
        self.assertEqual(rows[0]["kwh"], 12.3)

    def test_expand_daily_to_half_hours_sums(self):
        rows = eh.expand_daily_kwh_to_half_hours([{"date": "2026-07-27", "kwh": 24.0}])
        self.assertEqual(len(rows), 48)
        total = sum(r["kwh"] for r in rows)
        self.assertAlmostEqual(total, 24.0, places=3)

    def test_octopus_export_has_readings(self):
        now = datetime.now(UK_TZ)
        start_ms = int(now.timestamp() * 1000) - 3_600_000
        self.assertTrue(
            eh.octopus_export_has_readings([{"start_ms": start_ms, "kwh": 0.2}], days=14)
        )
        self.assertFalse(eh.octopus_export_has_readings([{"start_ms": start_ms, "kwh": 0}], days=14))
        self.assertFalse(eh.octopus_export_has_readings([], days=14))


if __name__ == "__main__":
    unittest.main()
