"""Unit tests for performance reporting (no Home Assistant required)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
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


virtual_temp = _load_module("perf_virtual_temp", "performance/virtual_panel_temp.py")
clipping = _load_module("perf_clipping", "performance/clipping.py")
financial = _load_module("perf_financial", "performance/financial.py")
store_mod = _load_module("perf_store", "performance/store.py")
solar_analysis = _load_module("perf_solar_analysis", "performance/solar_analysis.py")
physics_insights = _load_module("perf_physics_insights", "performance/physics_insights.py")
hems_audit = _load_module("perf_hems_audit", "performance/hems_audit.py")

import types

_pkg = types.ModuleType("foxess_plant")
_pkg.__path__ = [str(PKG_ROOT)]
sys.modules.setdefault("foxess_plant", _pkg)
sys.modules["foxess_plant.tariff_currency"] = _load_module(
    "foxess_plant.tariff_currency", "tariff_currency.py"
)
models = _load_module("foxess_plant.models", "models.py")


class VirtualPanelTempTests(unittest.TestCase):
    def test_cold_panel_above_baseline_voltage(self) -> None:
        temp = virtual_temp.compute_virtual_panel_temp_c(
            string_voltage_v=408.0,
            pv_power_kw=2.0,
            baseline_v_at_25c=400.0,
            temp_coefficient_v_per_c=-0.003,
        )
        self.assertIsNotNone(temp)
        assert temp is not None
        self.assertLess(temp, 25.0)

    def test_hot_panel_below_baseline_voltage(self) -> None:
        temp = virtual_temp.compute_virtual_panel_temp_c(
            string_voltage_v=392.0,
            pv_power_kw=3.0,
            baseline_v_at_25c=400.0,
            temp_coefficient_v_per_c=-0.003,
        )
        self.assertIsNotNone(temp)
        assert temp is not None
        self.assertGreater(temp, 25.0)

    def test_none_when_pv_idle(self) -> None:
        self.assertIsNone(
            virtual_temp.compute_virtual_panel_temp_c(
                string_voltage_v=400.0,
                pv_power_kw=0.05,
                baseline_v_at_25c=400.0,
            )
        )


class ClippingTests(unittest.TestCase):
    def test_no_clipping_below_threshold(self) -> None:
        self.assertEqual(
            clipping.compute_clipping_loss_kw(pv_power_kw=4.0, inverter_ac_limit_kw=4.3),
            0.0,
        )

    def test_clipping_when_at_limit(self) -> None:
        loss = clipping.compute_clipping_loss_kw(
            pv_power_kw=4.5,
            inverter_ac_limit_kw=4.3,
            recent_peak_kw=4.6,
        )
        self.assertGreater(loss, 0.0)


class FinancialTests(unittest.TestCase):
    def test_avoided_cost_included(self) -> None:
        row = financial.bucket_financials_gbp(
            import_kwh=0.1,
            export_kwh=0.2,
            load_kwh=0.5,
            import_p_per_kwh=30.0,
            export_p_per_kwh=15.0,
        )
        self.assertGreater(row["avoided_grid_cost_gbp"], 0.0)
        self.assertAlmostEqual(
            row["net_bucket_gbp"],
            row["export_earnings_gbp"] + row["avoided_grid_cost_gbp"] - row["import_spend_gbp"],
            places=4,
        )


class PerformanceStoreTests(unittest.TestCase):
    def test_ledger_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            s = store_mod.PerformanceStore(db)
            s.init_schema()
            s.upsert_daily_ledger(
                {
                    "date": "2026-07-10",
                    "pv_kwh": 12.5,
                    "solcast_forecast_kwh": 11.0,
                    "forecast_accuracy_pct": 113.6,
                    "export_kwh": 1.0,
                    "import_kwh": 2.0,
                    "export_earnings_gbp": 0.15,
                    "import_spend_gbp": 0.60,
                    "avoided_grid_cost_gbp": 1.20,
                    "clipping_loss_kwh": 0.1,
                    "clipping_loss_valuation_gbp": 0.02,
                    "net_daily_savings_gbp": 0.75,
                    "peak_power_kw": 4.5,
                    "peak_vs_rated_pct": 104.7,
                    "virtual_temp_min_c": 18.0,
                    "virtual_temp_max_c": 42.0,
                    "wind_correlation_note": None,
                    "solar_day_class": "under_forecast",
                    "insight_note": "113% of Solcast",
                }
            )
            row = s.get_daily_ledger("2026-07-10")
            assert row is not None
            self.assertAlmostEqual(row["net_daily_savings_gbp"], 0.75)
            self.assertAlmostEqual(s.sum_net_savings(), 0.75)

    def test_period_aggregate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            s = store_mod.PerformanceStore(db)
            s.init_schema()
            for day, savings in [("2026-07-08", 0.5), ("2026-07-09", 0.75), ("2026-07-10", 1.0)]:
                s.upsert_daily_ledger(
                    {
                        "date": day,
                        "pv_kwh": 10.0,
                        "solcast_forecast_kwh": 9.0,
                        "forecast_accuracy_pct": 111.0,
                        "export_kwh": 1.0,
                        "import_kwh": 2.0,
                        "export_earnings_gbp": 0.15,
                        "import_spend_gbp": 0.60,
                        "avoided_grid_cost_gbp": 1.20,
                        "clipping_loss_kwh": 0.0,
                        "clipping_loss_valuation_gbp": 0.0,
                        "net_daily_savings_gbp": savings,
                        "peak_power_kw": 4.0,
                        "peak_vs_rated_pct": 93.0,
                        "virtual_temp_min_c": None,
                        "virtual_temp_max_c": None,
                        "wind_correlation_note": None,
                        "solar_day_class": "under_forecast",
                        "insight_note": "Above forecast",
                    }
                )
            agg = s.period_aggregate("2026-07-08", "2026-07-10")
            self.assertEqual(agg["days"], 3)
            self.assertAlmostEqual(agg["net_daily_savings_gbp"], 2.25)
            rows = s.list_ledger_between("2026-07-08", "2026-07-10")
            self.assertEqual(len(rows), 3)


class SolarAnalysisTests(unittest.TestCase):
    def test_under_forecast_classification(self) -> None:
        self.assertEqual(
            solar_analysis.classify_forecast_day(forecast_accuracy_pct=115.0, peak_vs_rated_pct=95.0),
            solar_analysis.SOLAR_CLASS_UNDER_FORECAST,
        )

    def test_payback_summary_paid_off(self) -> None:
        result = solar_analysis.payback_summary(
            total_saved_gbp=9000.0,
            install_cost_gbp=8000.0,
            avg_daily_savings_gbp=2.5,
        )
        self.assertEqual(result["break_even_date"], "paid_off")
        self.assertEqual(result["payback_progress_pct"], 100.0)


class PhysicsInsightsTests(unittest.TestCase):
    def test_clipping_insight_when_sustained(self) -> None:
        clip = [{"t": float(i * 300000), "v": 0.2} for i in range(6)]
        notes = physics_insights.build_intraday_physics_insights(
            {"clipping_loss_kw": clip},
            ac_limit_kw=4.3,
        )
        self.assertTrue(any("clipping" in n.lower() for n in notes))

    def test_cloud_flush_detects_cold_then_peak(self) -> None:
        temp = [
            {"t": 1000.0, "v": 22.0},
            {"t": 2000.0, "v": 14.0},
            {"t": 3000.0, "v": 16.0},
        ]
        pv = [
            {"t": 1000.0, "v": 1.0},
            {"t": 2500.0, "v": 4.5},
            {"t": 3500.0, "v": 3.0},
        ]
        notes = physics_insights.build_intraday_physics_insights(
            {"virtual_panel_temp_c": temp, "pv_power_kw": pv},
            ac_limit_kw=4.3,
        )
        self.assertTrue(any("cloud-edge" in n.lower() for n in notes))


class HemsAuditTests(unittest.TestCase):
    def test_daily_plan_signature_stable(self) -> None:
        plan = [{"action": "export", "start": "14:00", "end": "15:00", "reason": "peak"}]
        self.assertEqual(hems_audit.daily_plan_signature(plan), hems_audit.daily_plan_signature(plan))

    def test_list_events_between(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "audit.db"
            s = store_mod.PerformanceStore(db)
            s.init_schema()
            s.log_event(
                ts="2026-07-10T12:00:00",
                event_type=hems_audit.EVENT_EXPORT_ARMED,
                payload_json=json.dumps({"reason": "test"}),
            )
            rows = s.list_events_between("2026-07-10T00:00:00", "2026-07-10T23:59:59")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["payload"]["reason"], "test")

    def test_audit_report_summary(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "audit.db"
            s = store_mod.PerformanceStore(db)
            s.init_schema()
            s.log_event(
                ts="2026-07-10T08:00:00",
                event_type=hems_audit.EVENT_DAILY_PLAN,
                payload_json=json.dumps({"slot_count": 3, "charge_slots": 1, "export_slots": 2}),
            )
            report = hems_audit.build_hems_audit_report(
                s, start_date="2026-07-10", end_date="2026-07-10"
            )
            self.assertEqual(report["event_count"], 1)
            self.assertIn("3 slots", report["events"][0]["summary"])


class PerformanceConfigSaveTests(unittest.TestCase):
    def test_from_dict_accepts_string_install_cost(self) -> None:
        cfg = models.PerformanceConfig.from_dict({"system_install_cost_gbp": "8500"})
        self.assertEqual(cfg.system_install_cost_gbp, 8500.0)

    def test_save_merge_round_trip(self) -> None:
        existing = models.PerformanceConfig(system_install_cost_gbp=None)
        payload = {"system_install_cost_gbp": 8500.0}
        merged = {**existing.to_dict(), **payload}
        cfg = models.PerformanceConfig.from_dict(merged)
        self.assertEqual(cfg.system_install_cost_gbp, 8500.0)
        self.assertEqual(cfg.to_dict()["system_install_cost_gbp"], 8500.0)


class PvInstallCostMigrationTests(unittest.TestCase):
    def test_merges_legacy_pv_minor_when_performance_unset(self) -> None:
        perf = models.PerformanceConfig(system_install_cost_gbp=None)
        merged = models.merge_legacy_pv_install_cost_into_performance(
            perf,
            {
                "pv1": {"installation_cost_minor": 500000},
                "pv2": {"installation_cost_minor": 350000},
            },
            "GBP",
        )
        self.assertEqual(merged.system_install_cost_gbp, 8500.0)

    def test_keeps_performance_cost_when_set(self) -> None:
        perf = models.PerformanceConfig(system_install_cost_gbp=12000.0)
        merged = models.merge_legacy_pv_install_cost_into_performance(
            perf,
            {"pv1": {"installation_cost_minor": 100000}},
            "GBP",
        )
        self.assertEqual(merged.system_install_cost_gbp, 12000.0)


if __name__ == "__main__":
    unittest.main()
