"""Unit tests for SmartCharge entity-mode rate parsing (no Home Assistant required)."""

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


entity_rates = _load_module("sc_entity_rates_test", "smart_charge/entity_rates.py")


class EntityRateParsingTests(unittest.TestCase):
    def test_api_format_row(self) -> None:
        row = entity_rates.normalize_entity_rate_row(
            {
                "valid_from": "2026-05-28T00:00:00+00:00",
                "valid_to": "2026-05-28T00:30:00+00:00",
                "value_inc_vat": 12.5,
            }
        )
        assert row is not None
        self.assertEqual(row["value_inc_vat"], 12.5)

    def test_integration_event_format_pounds(self) -> None:
        row = entity_rates.normalize_entity_rate_row(
            {
                "start": "2026-05-28T01:00:00+00:00",
                "end": "2026-05-28T01:30:00+00:00",
                "value_inc_vat": 0.15,
            }
        )
        assert row is not None
        self.assertAlmostEqual(row["value_inc_vat"], 15.0)

    def test_collect_rates_from_rates_attribute(self) -> None:
        attrs = {
            "rates": [
                {"start": "2026-05-28T00:00:00+00:00", "end": "2026-05-28T00:30:00+00:00", "value_inc_vat": 0.08},
                {"start": "2026-05-28T00:30:00+00:00", "end": "2026-05-28T01:00:00+00:00", "value_inc_vat": 0.09},
            ],
            "tariff_code": "E-1R-AGILE-24-10-01-A",
        }
        rows = entity_rates.collect_rate_rows_from_attributes(attrs)
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]["value_inc_vat"], 8.0)

    def test_merge_rate_rows_dedupes(self) -> None:
        rows = entity_rates.merge_rate_rows(
            [
                {"valid_from": "a", "value_inc_vat": 1.0},
                {"valid_from": "a", "value_inc_vat": 2.0},
                {"valid_from": "b", "value_inc_vat": 3.0},
            ]
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["value_inc_vat"], 1.0)


if __name__ == "__main__":
    unittest.main()
