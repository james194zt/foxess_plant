"""Unit tests for cheapest import slot selection (no Home Assistant required)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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


pick = _load_module("sc_import_slot_pick", "smart_charge/import_slot_pick.py")
spread_math = _load_module("sc_spread_math_winter", "smart_charge/spread_math.py")


@dataclass(frozen=True)
class _Slot:
    start: datetime
    end: datetime
    import_p_per_kwh: float
    export_p_per_kwh: float | None = None


class ImportTroughPickTests(unittest.TestCase):
    def test_prefers_deeper_negative_later(self) -> None:
        base = datetime(2026, 7, 29, 1, 0, tzinfo=timezone.utc)
        slots = [
            _Slot(base, base + timedelta(minutes=30), -0.04),
            _Slot(base + timedelta(hours=1), base + timedelta(hours=1, minutes=30), -0.05),
        ]
        best = pick.pick_best_import_slot(
            slots,
            current=base - timedelta(minutes=5),
            horizon=base + timedelta(hours=12),
            require_negative=True,
        )
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.import_p_per_kwh, -0.05)

    def test_cheapest_positive_within_cap(self) -> None:
        base = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
        slots = [
            _Slot(base, base + timedelta(minutes=30), 6.0),
            _Slot(base + timedelta(hours=1), base + timedelta(hours=1, minutes=30), 4.5),
            _Slot(base + timedelta(hours=2), base + timedelta(hours=2, minutes=30), 12.0),
        ]
        best = pick.pick_best_import_slot(
            slots,
            current=base - timedelta(minutes=5),
            horizon=base + timedelta(hours=12),
            max_import_p=8.0,
        )
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.import_p_per_kwh, 4.5)

    def test_trough_import_price(self) -> None:
        base = datetime(2026, 7, 29, 1, 0, tzinfo=timezone.utc)
        slots = [
            _Slot(base, base + timedelta(minutes=30), -0.04),
            _Slot(base + timedelta(hours=1), base + timedelta(hours=1, minutes=30), -0.05),
        ]
        self.assertEqual(pick.trough_import_price(slots, require_negative=True), -0.05)


class WinterFillCountTests(unittest.TestCase):
    def test_fill_when_solar_short_of_grid_gap(self) -> None:
        count = spread_math.winter_fill_slot_count(
            grid_gap_kwh=8.0,
            forecast_kwh=2.0,
            solar_margin=1.15,
            slot_kwh=0.5,
        )
        self.assertGreaterEqual(count, 1)

    def test_no_fill_when_solar_covers(self) -> None:
        count = spread_math.winter_fill_slot_count(
            grid_gap_kwh=2.0,
            forecast_kwh=10.0,
            solar_margin=1.15,
            slot_kwh=0.5,
        )
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
