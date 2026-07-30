"""Tests for NESO carbon intensity helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "foxess_plant"
PKG_NAME = "custom_components.foxess_plant"


def _install_ha_stubs() -> None:
    for name in (
        "homeassistant",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.util",
        "homeassistant.util.dt",
        "homeassistant.helpers.aiohttp_client",
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

# Stub octopus_greener deps for normalize_neso
GREEN_THRESHOLD = 99.0


def _score(gco2):
    if gco2 is None:
        return None
    return max(1, min(10, round(10 - (float(gco2) - 60) / 25)))


og_stub = types.ModuleType(f"{PKG_NAME}.octopus_greener")
og_stub.low_carbon_score_from_gco2 = _score
og_stub.is_low_carbon_green = lambda *, gco2=None, score=None: (score if score is not None else _score(gco2) or 0) >= 8
og_stub._parse_period_start = lambda raw: datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
sys.modules[f"{PKG_NAME}.octopus_greener"] = og_stub

_spec = importlib.util.spec_from_file_location(
    f"{PKG_NAME}.carbon_intensity_neso", PKG / "carbon_intensity_neso.py"
)
ci = importlib.util.module_from_spec(_spec)
sys.modules[f"{PKG_NAME}.carbon_intensity_neso"] = ci
_spec.loader.exec_module(ci)


class TestCarbonIntensityNeso(unittest.TestCase):
    def test_outward_postcode(self):
        self.assertEqual(ci.outward_postcode("SW1A 1AA"), "SW1A")
        self.assertEqual(ci.outward_postcode("rg10 9nn"), "RG10")

    def test_union_prefers_later_duplicate(self):
        a = [{"start_ms": 1000, "end_ms": 2000, "gco2_per_kwh": 10}]
        b = [{"start_ms": 1000, "end_ms": 2000, "gco2_per_kwh": 99}, {"start_ms": 2000, "end_ms": 3000, "gco2_per_kwh": 50}]
        merged = ci.union_carbon_periods(a, b)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["gco2_per_kwh"], 99)

    def test_covers_horizon(self):
        now = datetime.now(timezone.utc)
        now_ms = int(now.timestamp() * 1000)
        short = [{"start_ms": now_ms, "end_ms": now_ms + 6 * 3600 * 1000}]
        long = [{"start_ms": now_ms, "end_ms": now_ms + 30 * 3600 * 1000}]
        self.assertFalse(ci.carbon_covers_horizon(short, now_ms=now_ms, hours=22))
        self.assertTrue(ci.carbon_covers_horizon(long, now_ms=now_ms, hours=22))

    def test_normalize_neso_rows(self):
        start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        rows = [
            {
                "from": start.isoformat().replace("+00:00", "Z"),
                "to": (start + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
                "intensity": {"forecast": 80, "index": "low"},
            }
        ]
        periods = ci.normalize_neso_carbon_periods(rows)
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0]["gco2_per_kwh"], 80.0)
        self.assertEqual(periods[0]["source"], "neso")


if __name__ == "__main__":
    unittest.main()
