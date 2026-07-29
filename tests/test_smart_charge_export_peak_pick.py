"""Unit tests for peak export slot selection (no Home Assistant required)."""

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


pick = _load_module("sc_export_slot_pick", "smart_charge/export_slot_pick.py")


@dataclass(frozen=True)
class _Slot:
    start: datetime
    end: datetime
    import_p_per_kwh: float
    export_p_per_kwh: float | None = None


class PeakExportPickTests(unittest.TestCase):
    def test_prefers_21p_over_earlier_18p(self) -> None:
        base = datetime(2026, 7, 29, 17, 0, tzinfo=timezone.utc)
        slots = [
            _Slot(base + timedelta(hours=1), base + timedelta(hours=1, minutes=30), 40.0, 18.0),
            _Slot(base + timedelta(hours=2), base + timedelta(hours=2, minutes=30), 45.0, 21.0),
        ]
        best = pick.pick_best_export_slot(
            slots,
            min_export_p=15.0,
            current=base,
            horizon=base + timedelta(hours=12),
        )
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.export_p_per_kwh, 21.0)
        self.assertEqual(best.start, slots[1].start)

    def test_ignores_below_threshold(self) -> None:
        base = datetime(2026, 7, 29, 17, 0, tzinfo=timezone.utc)
        slots = [
            _Slot(base + timedelta(hours=1), base + timedelta(hours=1, minutes=30), 40.0, 12.0),
            _Slot(base + timedelta(hours=2), base + timedelta(hours=2, minutes=30), 45.0, 16.0),
        ]
        best = pick.pick_best_export_slot(
            slots,
            min_export_p=15.0,
            current=base,
            horizon=base + timedelta(hours=12),
        )
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.export_p_per_kwh, 16.0)

    def test_peak_export_price(self) -> None:
        base = datetime(2026, 7, 29, 17, 0, tzinfo=timezone.utc)
        slots = [
            _Slot(base, base + timedelta(minutes=30), 40.0, 18.0),
            _Slot(base + timedelta(hours=1), base + timedelta(hours=1, minutes=30), 45.0, 21.0),
        ]
        self.assertEqual(pick.peak_export_price(slots, min_export_p=15.0), 21.0)
        self.assertIsNone(pick.peak_export_price(slots, min_export_p=30.0))


if __name__ == "__main__":
    unittest.main()
