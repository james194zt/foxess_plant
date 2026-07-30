"""Tests for Octopus analysis price/carbon merge helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "foxess_plant"
PKG_NAME = "custom_components.foxess_plant"

GREEN_THRESHOLD_GCO2 = 99.0
CARBON_SCORE_BASE = 60.0
CARBON_SCORE_SCALE = 25.0


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
    dt.utc_from_timestamp = lambda value: datetime.fromtimestamp(value, timezone.utc)
    dt.now = lambda tz=None: datetime.now(tz or timezone.utc)
    dt.parse_datetime = lambda raw: datetime.fromisoformat(str(raw).replace("Z", "+00:00"))


def low_carbon_score_from_gco2(value: float | None) -> int | None:
    if value is None:
        return None
    try:
        gco2 = float(value)
    except (TypeError, ValueError):
        return None
    score = round(10 - (gco2 - CARBON_SCORE_BASE) / CARBON_SCORE_SCALE)
    return max(1, min(10, score))


def is_low_carbon_green(*, gco2: float | None = None, score: int | None = None) -> bool:
    if score is None:
        score = low_carbon_score_from_gco2(gco2)
    if score is None:
        return False
    return score >= (low_carbon_score_from_gco2(GREEN_THRESHOLD_GCO2) or 8)


def _ensure_pkg() -> None:
    sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
    if PKG_NAME not in sys.modules:
        pkg = types.ModuleType(PKG_NAME)
        pkg.__path__ = [str(PKG)]
        sys.modules[PKG_NAME] = pkg


def _stub_sub(mod_name: str, **attrs):
    _ensure_pkg()
    full = f"{PKG_NAME}.{mod_name}"
    stub = types.ModuleType(full)
    for key, value in attrs.items():
        setattr(stub, key, value)
    sys.modules[full] = stub
    return stub


_install_ha_stubs()
_stub_sub(
    "octopus_greener",
    GREEN_THRESHOLD_GCO2=GREEN_THRESHOLD_GCO2,
    is_low_carbon_green=is_low_carbon_green,
    low_carbon_score_from_gco2=low_carbon_score_from_gco2,
    normalize_carbon_periods=lambda rows: rows,
)
_stub_sub(
    "octopus_api",
    OctopusApiClient=type("OctopusApiClient", (), {}),
    OctopusApiError=type("OctopusApiError", (Exception,), {}),
)
_stub_sub("octopus_consumption_store", OctopusConsumptionStore=type("OctopusConsumptionStore", (), {}))
_stub_sub(
    "octopus_tariff",
    _parse_api_dt=lambda raw: None,
    _rate_value_inc_vat=lambda row: None,
    is_variable_tariff_type=lambda raw: "agile" in str(raw).lower(),
    product_code_from_tariff_code=lambda raw: None,
    resolve_meter_for_consumption=lambda cache, export=False: {},
)

_ensure_pkg()
_spec = importlib.util.spec_from_file_location(
    f"{PKG_NAME}.octopus_analysis", PKG / "octopus_analysis.py"
)
oa = importlib.util.module_from_spec(_spec)
sys.modules[f"{PKG_NAME}.octopus_analysis"] = oa
_spec.loader.exec_module(oa)


class TestMergePriceAndCarbon(unittest.TestCase):
    def test_matches_carbon_by_containing_interval(self):
        rate_slots = [{"start_ms": 1_000, "end_ms": 1_800_000, "p_per_kwh": 12.5}]
        carbon = [
            {
                "start_ms": 0,
                "end_ms": 1_800_000,
                "gco2_per_kwh": 85.0,
                "low_carbon_score": 9,
            }
        ]
        merged = oa.merge_price_and_carbon(rate_slots, carbon)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["low_carbon_score"], 9)
        self.assertEqual(merged[0]["gco2_per_kwh"], 85.0)
        self.assertTrue(merged[0]["is_green"])

    def test_matches_when_start_ms_types_differ(self):
        rate_slots = [{"start_ms": 1_800_000, "end_ms": 3_600_000, "p_per_kwh": 10.0}]
        carbon = [
            {
                "start_ms": 1_800_000.0,
                "end_ms": 3_600_000.0,
                "gco2_per_kwh": 150.0,
                "low_carbon_score": 6,
            }
        ]
        merged = oa.merge_price_and_carbon(rate_slots, carbon)
        self.assertEqual(merged[0]["low_carbon_score"], 6)
        self.assertFalse(merged[0]["is_green"])

    def test_dashboard_payload_rebuilds_dual_from_greener_carbon(self):
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        end_ms = now_ms + 1_800_000
        snapshot = {
            "import_rate_slots": [
                {"start_ms": now_ms, "end_ms": end_ms, "p_per_kwh": 11.0},
            ],
            "export_rate_slots": [],
            "dual_periods": [
                {
                    "start_ms": now_ms,
                    "end_ms": end_ms,
                    "p_per_kwh": 11.0,
                    "low_carbon_score": None,
                    "gco2_per_kwh": None,
                }
            ],
            "tariff_type": "agile",
        }
        greener = {
            "carbon_periods": [
                {
                    "start_ms": now_ms,
                    "end_ms": end_ms,
                    "gco2_per_kwh": 70.0,
                    "low_carbon_score": 10,
                }
            ],
            "title": "Greener",
        }
        payload = oa.octopus_analysis_dashboard_payload(snapshot, greener_payload=greener)
        self.assertEqual(payload["dual_periods"][0]["low_carbon_score"], 10)
        self.assertEqual(payload["carbon_periods"][0]["low_carbon_score"], 10)


class TestDailyMeterCosts(unittest.TestCase):
    def test_rate_p_at_ms_finds_window(self):
        periods = [
            {"start_ms": 0, "end_ms": 1_800_000, "p_per_kwh": 10.0},
            {"start_ms": 1_800_000, "end_ms": 3_600_000, "p_per_kwh": 25.5},
        ]
        self.assertEqual(oa.rate_p_at_ms(900_000, periods), 10.0)
        self.assertEqual(oa.rate_p_at_ms(1_800_000, periods), 25.5)
        self.assertIsNone(oa.rate_p_at_ms(3_600_000, periods))

    def test_compute_daily_meter_costs_joins_kwh_and_rates(self):
        # Two half-hours on 2026-07-28 UK morning
        day = datetime(2026, 7, 28, 1, 0, tzinfo=timezone.utc)
        t0 = int(day.timestamp() * 1000)
        t1 = t0 + 1_800_000
        import_rows = [
            {"start_ms": t0, "kwh": 2.0},
            {"start_ms": t1, "kwh": 1.0},
        ]
        export_rows = [{"start_ms": t0, "kwh": 4.0}]
        import_rates = [
            {"start_ms": t0, "end_ms": t1, "p_per_kwh": 20.0},
            {"start_ms": t1, "end_ms": t1 + 1_800_000, "p_per_kwh": 10.0},
        ]
        export_rates = [{"start_ms": t0, "end_ms": t1 + 1_800_000, "p_per_kwh": 15.0}]
        result = oa.compute_daily_meter_costs(
            import_rows,
            export_rows,
            import_rates,
            export_rates,
            days=14,
            now=datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(len(result["days"]), 1)
        day_row = result["days"][0]
        # import: 2*0.20 + 1*0.10 = 0.50
        self.assertAlmostEqual(day_row["import_spend_gbp"], 0.5, places=4)
        # export: 4*0.15 = 0.60
        self.assertAlmostEqual(day_row["export_earnings_gbp"], 0.6, places=4)
        self.assertAlmostEqual(day_row["net_gbp"], 0.1, places=4)
        self.assertEqual(result["priced_import_intervals"], 2)
        self.assertEqual(result["priced_export_intervals"], 1)

    def test_unpriced_intervals_counted(self):
        t0 = int(datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
        result = oa.compute_daily_meter_costs(
            [{"start_ms": t0, "kwh": 1.0}],
            [],
            [],
            [],
            days=14,
            now=datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(result["unpriced_import_intervals"], 1)
        self.assertEqual(result["days"][0]["import_spend_gbp"], 0.0)
        self.assertEqual(result["days"][0]["import_kwh"], 1.0)


if __name__ == "__main__":
    unittest.main()
