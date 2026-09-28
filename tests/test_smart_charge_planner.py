"""Scenario tests for the SmartCharge planner (no Home Assistant required)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

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


planner = _load_module("sc_planner_test", "smart_charge/planner.py")
load_profile = _load_module("sc_load_profile_test", "smart_charge/load_profile.py")

TZ = ZoneInfo("Europe/London")
UTC = timezone.utc


def local(y, mo, d, h, mi=0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=TZ)


def agile_rows(start: datetime, hours: int, price_fn) -> list[dict]:
    rows = []
    t = start.astimezone(UTC)
    for _ in range(hours * 2):
        rows.append(
            {
                "valid_from": t.isoformat(),
                "valid_to": (t + timedelta(minutes=30)).isoformat(),
                "value_inc_vat": price_fn(t.astimezone(TZ)),
            }
        )
        t += timedelta(minutes=30)
    return rows


def overnight_cheap(local_dt: datetime) -> float:
    if 0 <= local_dt.hour < 5:
        return 7.0
    if 16 <= local_dt.hour < 19:
        return 35.0
    return 25.0


def solar_rows(day: datetime, total_kwh: float) -> list[dict]:
    """Bell-ish PV curve between 08:00 and 18:00 local summing to ``total_kwh``."""
    weights = []
    t = day.replace(hour=8, minute=0)
    while t.hour < 18:
        x = (t.hour + t.minute / 60.0 - 13.0) / 5.0
        weights.append((t, max(0.0, 1 - x * x)))
        t += timedelta(minutes=30)
    total_w = sum(w for _, w in weights)
    return [
        {"period_start": t.astimezone(UTC).isoformat(), "pv_estimate": total_kwh * w / total_w / 0.5}
        for t, w in weights
    ]


def flat_profile(kw: float) -> dict:
    return {"all": [kw * 0.5] * 48}


def params(**kw) -> "planner.PlanParams":
    base = dict(
        capacity_kwh=10.0,
        floor_kwh=1.0,
        cap_kwh=10.0,
        charge_kw=3.0,
        discharge_kw=3.0,
        round_trip_efficiency=0.9,
        export_allowed=False,
        min_saving_p_per_kwh=1.0,
    )
    base.update(kw)
    return planner.PlanParams(**base)


def run(now, import_rows, forecast_rows, *, soc_kwh=5.0, export_rows=None, load_kw=0.42, p=None):
    slots = planner.build_timeline(
        now=now,
        tz=TZ,
        import_rows=import_rows,
        export_rows=export_rows,
        forecast_rows=forecast_rows,
        load_profile=flat_profile(load_kw),
    )
    plan, summary = planner.build_plan(slots, soc_kwh, p or params(), tz=TZ, now=now)
    return slots, plan, summary


def charge_slots(plan):
    return [e for e in plan if e["action"] == "charge"]


class TimelineTests(unittest.TestCase):
    def test_flat_open_ended_row_splits_into_half_hours(self) -> None:
        now = local(2026, 1, 10, 16, 10)
        rows = [{"valid_from": "2025-01-01T00:00:00Z", "valid_to": None, "value_inc_vat": 24.5}]
        slots = planner.build_timeline(now=now, tz=TZ, import_rows=rows, load_profile=flat_profile(0.4))
        self.assertTrue(all(abs((s.end - s.start).total_seconds() - 1800) < 1 for s in slots))
        self.assertTrue(all(s.price_known and s.import_p == 24.5 for s in slots))
        # First slot is partial (16:10 -> 16:30) and covers through end of tomorrow.
        self.assertAlmostEqual(slots[0].hours, 20 / 60, places=3)
        self.assertEqual(slots[-1].end.astimezone(TZ), local(2026, 1, 12, 0, 0))

    def test_go_rows_keep_half_hour_boundaries(self) -> None:
        now = local(2026, 1, 10, 20, 0)
        rows = [
            {"valid_from": local(2026, 1, 10, 4, 30).astimezone(UTC).isoformat(),
             "valid_to": local(2026, 1, 11, 0, 30).astimezone(UTC).isoformat(), "value_inc_vat": 27.0},
            {"valid_from": local(2026, 1, 11, 0, 30).astimezone(UTC).isoformat(),
             "valid_to": local(2026, 1, 11, 4, 30).astimezone(UTC).isoformat(), "value_inc_vat": 8.5},
            {"valid_from": local(2026, 1, 11, 4, 30).astimezone(UTC).isoformat(),
             "valid_to": local(2026, 1, 12, 0, 30).astimezone(UTC).isoformat(), "value_inc_vat": 27.0},
        ]
        slots = planner.build_timeline(now=now, tz=TZ, import_rows=rows, load_profile=flat_profile(0.4))
        cheap = [s for s in slots if s.import_p == 8.5]
        self.assertEqual(cheap[0].start.astimezone(TZ), local(2026, 1, 11, 0, 30))
        self.assertEqual(cheap[-1].end.astimezone(TZ), local(2026, 1, 11, 4, 30))

    def test_unpublished_prices_are_estimated_and_flagged(self) -> None:
        now = local(2026, 1, 10, 10, 0)
        rows = agile_rows(local(2026, 1, 10, 10, 0), 13, overnight_cheap)  # up to 23:00 today
        slots = planner.build_timeline(now=now, tz=TZ, import_rows=rows, load_profile=flat_profile(0.4))
        unknown = [s for s in slots if not s.price_known]
        self.assertTrue(unknown)
        self.assertEqual(unknown[0].start.astimezone(TZ), local(2026, 1, 10, 23, 0))

    def test_schedule_rows_sampled_every_half_hour(self) -> None:
        now = local(2026, 1, 10, 2, 15)

        def rate_at(dt):
            return {"import_p_per_kwh": 9.0 if 0 <= dt.hour < 5 else 28.0}

        rows = planner.schedule_rate_rows(rate_at, now=now, tz=TZ)
        self.assertEqual(planner.parse_iso(rows[0]["valid_from"]).astimezone(TZ), local(2026, 1, 10, 2, 0))
        self.assertEqual(rows[0]["value_inc_vat"], 9.0)


class TariffProfileTests(unittest.TestCase):
    NOW = local(2026, 3, 10, 12, 0)

    @staticmethod
    def flat(p):
        return [{"valid_from": "2025-01-01T00:00:00Z", "valid_to": None, "value_inc_vat": p}]

    def test_flat_import_fixed_seg_export_hides_forced_export(self) -> None:
        prof = planner.tariff_profile(self.flat(24.5), self.flat(15.0), self.NOW)
        self.assertFalse(prof["import_varies"])
        self.assertFalse(prof["export_varies"])
        self.assertTrue(prof["has_export"])
        self.assertFalse(prof["forced_export_useful"])

    def test_agile_import_fixed_outgoing_export_is_useful(self) -> None:
        prof = planner.tariff_profile(agile_rows(self.NOW, 30, overnight_cheap), self.flat(15.0), self.NOW)
        self.assertTrue(prof["import_varies"])
        self.assertFalse(prof["export_varies"])
        self.assertTrue(prof["forced_export_useful"])

    def test_no_export_tariff(self) -> None:
        prof = planner.tariff_profile(self.flat(24.5), [], self.NOW)
        self.assertFalse(prof["has_export"])
        self.assertFalse(prof["export_known"])
        self.assertFalse(prof["forced_export_useful"])

    def test_agile_outgoing_varies(self) -> None:
        exports = agile_rows(self.NOW, 30, lambda t: 30.0 if 16 <= t.hour < 19 else 8.0)
        prof = planner.tariff_profile(self.flat(24.5), exports, self.NOW)
        self.assertTrue(prof["export_varies"])
        self.assertTrue(prof["forced_export_useful"])


class SolcastRowTests(unittest.TestCase):
    def test_period_end_rows_cover_preceding_half_hour(self) -> None:
        # Fox Plant merged rows: period_start == period_end == Solcast period END.
        end = local(2026, 6, 1, 12, 30).astimezone(UTC).isoformat()
        rows = [{"period_start": end, "period_end": end, "pv_estimate": 2.0}]
        start, stop, kw = planner._pv_intervals(rows)[0]
        self.assertEqual(start.astimezone(TZ), local(2026, 6, 1, 12, 0))
        self.assertEqual(stop.astimezone(TZ), local(2026, 6, 1, 12, 30))
        self.assertEqual(planner.forecast_end(rows).astimezone(TZ), local(2026, 6, 1, 12, 30))

    def test_tomorrow_pv_counted_when_forecast_covers_tomorrow(self) -> None:
        now = local(2026, 6, 1, 20, 0)
        rates = agile_rows(now, 28, overnight_cheap)
        _slots, _plan, summary = run(now, rates, solar_rows(local(2026, 6, 2, 0), 18.0))
        self.assertAlmostEqual(summary.tomorrow_pv_kwh, 18.0, places=1)


class PlannerScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = local(2026, 3, 10, 16, 0)
        self.rates = agile_rows(self.now, 31, overnight_cheap)  # to 23:00 tomorrow

    def test_sunny_tomorrow_needs_no_grid_charge(self) -> None:
        forecast = solar_rows(local(2026, 3, 11, 0), 25.0)
        _slots, plan, summary = run(self.now, self.rates, forecast, soc_kwh=8.0, load_kw=0.3)
        self.assertEqual(charge_slots(plan), [], summary.to_dict())

    def test_cloudy_tomorrow_charges_overnight_sized_to_shortfall(self) -> None:
        forecast = solar_rows(local(2026, 3, 11, 0), 3.0)
        _slots, plan, summary = run(self.now, self.rates, forecast, soc_kwh=2.0)
        charges = charge_slots(plan)
        self.assertTrue(charges)
        for entry in charges:
            start = planner.parse_iso(entry["start_utc"]).astimezone(TZ)
            self.assertLess(start.hour, 5, entry)
            self.assertEqual(entry["import_p_per_kwh"], 7.0)
        # More than one half-hour: a 3 kW charger can't cover the day in 30 minutes.
        self.assertGreater(len(charges), 1)
        self.assertGreater(summary.grid_charge_kwh, 3.0)

    def test_never_charge_to_avoid_slightly_dearer_import(self) -> None:
        rows = agile_rows(self.now, 31, lambda t: 24.0 if t.hour < 5 else 24.5)
        _slots, plan, _ = run(self.now, rows, [], soc_kwh=1.0)
        self.assertEqual(charge_slots(plan), [])

    def test_flat_tariff_never_grid_charges(self) -> None:
        rows = [{"valid_from": "2025-01-01T00:00:00Z", "valid_to": None, "value_inc_vat": 24.5}]
        _slots, plan, _ = run(self.now, rows, [], soc_kwh=1.0)
        self.assertEqual(charge_slots(plan), [])

    def test_negative_price_charges(self) -> None:
        rows = agile_rows(self.now, 31, lambda t: -5.0 if (t.hour == 13 and t.day == 11) else 20.0)
        forecast = solar_rows(local(2026, 3, 11, 0), 2.0)
        _slots, plan, _ = run(self.now, rows, forecast, soc_kwh=3.0)
        charges = charge_slots(plan)
        self.assertTrue(charges)
        self.assertTrue(all(e["import_p_per_kwh"] < 0 for e in charges), charges)

    def test_plunge_always_charges_even_when_pv_fills_battery(self) -> None:
        # Cheap overnight + strong PV fill the battery before the plunge; the plunge
        # must still be a force charge (to max SOC) so the house imports at the paid rate.
        def price(t):
            if t.day == 11 and 12 <= t.hour < 14:
                return -0.5  # below the 1p minimum saving: the rule is not economic
            return overnight_cheap(t)

        rows = agile_rows(self.now, 31, price)
        forecast = solar_rows(local(2026, 3, 11, 0), 30.0)
        p = params(cap_kwh=9.0)
        _slots, plan, _ = run(self.now, rows, forecast, soc_kwh=9.0, p=p)
        plunge = [e for e in plan if e["import_p_per_kwh"] < 0]
        self.assertEqual(len(plunge), 4)
        for entry in plunge:
            self.assertEqual(entry["action"], "charge", entry)
            self.assertEqual(entry["reason"], "negative_import")
            self.assertEqual(entry["target_soc_pct"], 90.0)
        d = planner.decide(plan, planner.parse_iso(plunge[1]["start_utc"]) + timedelta(minutes=5))
        self.assertEqual(d["action"], "arbitrage")
        self.assertEqual(d["target_soc_pct"], 90.0)
        self.assertEqual(d["window"]["start_utc"], plunge[0]["start_utc"])

    def test_export_peak_with_cheap_refill(self) -> None:
        now = local(2026, 3, 10, 15, 0)
        imports = agile_rows(now, 32, overnight_cheap)
        exports = agile_rows(now, 32, lambda t: 30.0 if (16 <= t.hour < 17 and t.day == 10) else 5.0)
        p = params(export_allowed=True, min_export_p=12.0, export_floor_kwh=4.0)
        _slots, plan, _ = run(now, imports, [], soc_kwh=9.5, export_rows=exports, p=p)
        exports_planned = [e for e in plan if e["action"] == "export"]
        self.assertTrue(exports_planned)
        for entry in exports_planned:
            self.assertEqual(entry["export_p_per_kwh"], 30.0)
            self.assertGreaterEqual(entry["soc_end_pct"], 40.0 - 0.01)

    def test_agile_outgoing_exports_top_slots_with_a_budget_per_day(self) -> None:
        now = local(2026, 3, 10, 15, 0)
        imports = agile_rows(now, 32, overnight_cheap)
        peak = {16: 24.0, 17: 31.0, 18: 27.0}
        exports = agile_rows(now, 32, lambda t: peak.get(t.hour, 5.0))
        # Budget covers two 30-minute exports: day 1 used to spend all of it, leaving none for day 2.
        p = params(export_allowed=True, min_export_p=12.0, export_floor_kwh=4.0, max_export_kwh=3.0)
        _slots, plan, _ = run(now, imports, [], soc_kwh=10.0, export_rows=exports, p=p)
        for day in (10, 11):
            planned = [
                e for e in plan
                if e["action"] == "export" and planner.parse_iso(e["start_utc"]).astimezone(TZ).day == day
            ]
            self.assertTrue(planned, f"no export on day {day}")
            self.assertLessEqual(sum(e["planned_export_kwh"] for e in planned), 3.0 + 1e-6)
            # Only the best-paying hour is used when the budget is this small.
            self.assertTrue(all(e["export_p_per_kwh"] == 31.0 for e in planned), planned)
            self.assertGreaterEqual(min(e["soc_end_pct"] for e in planned), 40.0 - 0.01)

    def test_no_actions_in_unknown_price_slots(self) -> None:
        now = local(2026, 3, 10, 10, 0)
        rows = agile_rows(now, 13, overnight_cheap)
        _slots, plan, _ = run(now, rows, solar_rows(local(2026, 3, 11, 0), 2.0), soc_kwh=2.0)
        for entry in plan:
            if not entry["price_known"]:
                self.assertEqual(entry["action"], "idle")


def three_band(t: datetime) -> float:
    """E.ON-style time of use: cheap 02-05, peak 16-19, standard otherwise."""
    if 2 <= t.hour < 5:
        return 18.05
    if 16 <= t.hour < 19:
        return 45.25
    return 24.65


EVENING_PROFILE = {"all": [(1.5 if 34 <= i < 38 else 0.6 if 38 <= i < 44 else 0.25) * 0.5 for i in range(48)]}


def run_tou(now, soc_kwh, pv_kwh, *, peak_min_pct):
    rates = agile_rows(now, 40, three_band)
    exports = agile_rows(now, 40, lambda t: 13.0)
    slots = planner.build_timeline(
        now=now,
        tz=TZ,
        import_rows=rates,
        export_rows=exports,
        forecast_rows=solar_rows(local(2026, 9, 29, 0), pv_kwh),
        load_profile=EVENING_PROFILE,
    )
    p = params(charge_kw=3.6, discharge_kw=5.0, pv_scale=1 / 1.15, load_scale=1.1, topup_below_kwh=peak_min_pct / 10)
    plan, _ = planner.build_plan(slots, soc_kwh, p, tz=TZ, now=now)
    return plan


def on_day(plan, day, price):
    return [
        e for e in plan
        if planner.parse_iso(e["start_utc"]).astimezone(TZ).day == day and e["import_p_per_kwh"] == price
    ]


class TimeOfUseTests(unittest.TestCase):
    def test_charges_only_in_cheapest_band_and_covers_peak(self) -> None:
        for pv in (0.0, 4.0, 10.0, 20.0):
            plan = run_tou(local(2026, 9, 28, 19, 0), 3.0, pv, peak_min_pct=20)
            day_charges = [e for e in charge_slots(plan) if e["import_p_per_kwh"] != 18.05]
            self.assertEqual(day_charges, [], f"PV {pv}: unexpected daytime charge")
            peak = on_day(plan, 29, 45.25)
            self.assertEqual(sum(e["grid_import_kwh"] for e in peak), 0.0, f"PV {pv}")
            self.assertGreaterEqual(peak[-1]["soc_end_pct"], 20.0 - 0.1, f"PV {pv}")

    def test_sunny_day_leaves_room_for_pv(self) -> None:
        plan = run_tou(local(2026, 9, 28, 19, 0), 3.0, 20.0, peak_min_pct=20)
        night = on_day(plan, 29, 18.05)
        self.assertLess(night[-1]["soc_end_pct"], 50.0)

    def test_peak_lower_limit_holds_spare_through_peak(self) -> None:
        # No PV: the night charge alone ends the peak near 30%. A 40% limit must keep more back.
        plan = run_tou(local(2026, 9, 28, 19, 0), 3.0, 0.0, peak_min_pct=40)
        peak = on_day(plan, 29, 45.25)
        self.assertGreaterEqual(peak[-1]["soc_end_pct"], 40.0 - 0.1)
        self.assertEqual(sum(e["grid_import_kwh"] for e in peak), 0.0)

    def test_pv_shortfall_tops_up_before_peak_not_during(self) -> None:
        plan = run_tou(local(2026, 9, 29, 12, 0), 3.5, 2.0, peak_min_pct=20)
        top_ups = [e for e in charge_slots(on_day(plan, 29, 24.65))]
        self.assertTrue(top_ups)
        for e in top_ups:
            hour = planner.parse_iso(e["start_utc"]).astimezone(TZ).hour
            self.assertTrue(12 <= hour < 16, e)
        self.assertEqual(charge_slots(on_day(plan, 29, 45.25)), [])
        self.assertEqual(sum(e["grid_import_kwh"] for e in on_day(plan, 29, 45.25)), 0.0)

    def test_agile_is_not_restricted_to_one_band(self) -> None:
        now = local(2026, 3, 10, 16, 0)
        rows = agile_rows(now, 31, lambda t: 10.0 + (t.hour * 60 + t.minute) / 60.0)
        slots = planner.build_timeline(now=now, tz=TZ, import_rows=rows, load_profile=flat_profile(0.4))
        self.assertTrue(all(planner.cheapest_band_slots(slots)))


class DecideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = local(2026, 3, 10, 16, 0)
        rates = agile_rows(self.now, 31, overnight_cheap)
        forecast = solar_rows(local(2026, 3, 11, 0), 3.0)
        _slots, self.plan, _ = run(self.now, rates, forecast, soc_kwh=2.0)

    def test_committed_plan_is_stable_across_ticks(self) -> None:
        windows = set()
        t = self.now
        while t < local(2026, 3, 10, 23, 30):
            d = planner.decide(self.plan, t)
            self.assertEqual(d["action"], "idle")
            windows.add((d["next_charge"]["start_utc"], d["next_charge"]["end_utc"]))
            t += timedelta(minutes=15)
        self.assertEqual(len(windows), 1)

    def test_in_progress_charge_slot_arms_immediately(self) -> None:
        first = charge_slots(self.plan)[0]
        start = planner.parse_iso(first["start_utc"])
        d = planner.decide(self.plan, start + timedelta(minutes=15))
        self.assertEqual(d["action"], "grid_charge")
        self.assertEqual(d["window"]["start_utc"], first["start_utc"])
        self.assertGreater(d["target_soc_pct"], 20)

    def test_expected_soc_interpolates(self) -> None:
        entry = self.plan[3]
        start = planner.parse_iso(entry["start_utc"])
        mid = planner.expected_soc_pct(self.plan, start + timedelta(minutes=15))
        self.assertAlmostEqual(mid, (entry["soc_start_pct"] + entry["soc_end_pct"]) / 2, places=1)


class ParamsTests(unittest.TestCase):
    def test_modes(self) -> None:
        cfg = SimpleNamespace(operating_mode="max_safety", max_target_soc=100, export_min_soc=40,
                              max_charge_kw=3.6, solar_safety_margin=1.25)
        p = planner.params_from_config(cfg, capacity_kwh=10.0, reserve_kwh=2.0, inverter_min_soc_pct=10)
        self.assertAlmostEqual(p.floor_kwh, 2.0)
        self.assertAlmostEqual(p.pv_scale, 0.8)
        self.assertAlmostEqual(p.export_floor_kwh, 4.0)
        self.assertAlmostEqual(p.discharge_kw, 3.6)
        cfg.operating_mode = "max_green"
        p = planner.params_from_config(cfg, capacity_kwh=10.0, reserve_kwh=0.5, inverter_min_soc_pct=10)
        self.assertFalse(p.export_allowed)
        self.assertAlmostEqual(p.floor_kwh, 1.0)
        self.assertGreater(p.carbon_weight_p, 0)


class LoadProfileTests(unittest.TestCase):
    def _points(self, days: int, kwh_fn) -> list[dict]:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        pts = []
        total = 0.0
        for h in range(days * 24 + 1):
            t = start + timedelta(hours=h)
            total += kwh_fn(t)  # HA hourly "sum" = counter at the END of the hour
            pts.append({"start": t.timestamp(), "mean": total})
        return pts

    def test_profile_medians(self) -> None:
        pts = self._points(14, lambda t: 2.0 if t.hour == 18 else 0.4)
        hourly = load_profile.hourly_consumption(pts)
        profile = load_profile.build_load_profile(hourly, ZoneInfo("UTC"))
        self.assertIsNotNone(profile)
        self.assertAlmostEqual(profile["all"][18 * 2], 1.0)
        self.assertAlmostEqual(profile["all"][18 * 2 + 1], 1.0)
        self.assertAlmostEqual(profile["all"][3 * 2], 0.2)
        self.assertIn("weekday", profile)
        self.assertIn("weekend", profile)

    def test_short_history_has_no_weekend_split(self) -> None:
        pts = self._points(3, lambda t: 0.5)
        profile = load_profile.build_load_profile(load_profile.hourly_consumption(pts), ZoneInfo("UTC"))
        self.assertNotIn("weekend", profile)
        self.assertAlmostEqual(load_profile.average_load_kw(profile, 1.0), 0.5)

    def test_no_history_falls_back(self) -> None:
        self.assertIsNone(load_profile.build_load_profile([], ZoneInfo("UTC")))
        self.assertEqual(load_profile.average_load_kw(None, 0.7), 0.7)


def pv_rows(start: datetime, end: datetime, kw_fn) -> list[dict]:
    """Solcast-style period-end rows (period_start == period_end)."""
    rows = []
    t = start.astimezone(UTC)
    while t <= end.astimezone(UTC):
        iso = t.isoformat()
        rows.append({"period_start": iso, "period_end": iso, "pv_estimate": kw_fn(t.astimezone(TZ))})
        t += timedelta(minutes=30)
    return rows


def midday_kw(when: datetime) -> float:
    return 3.0 if 10 <= when.hour < 15 else 0.0


class ForecastGapTests(unittest.TestCase):
    def test_merge_keeps_older_poll_rows_beyond_latest(self) -> None:
        now = local(2026, 9, 27, 20)
        older = pv_rows(local(2026, 9, 27, 12), local(2026, 9, 29, 0), lambda _t: 1.0)
        latest = pv_rows(local(2026, 9, 27, 18), local(2026, 9, 28, 2), lambda _t: 2.0)
        merged = planner.merge_forecast_snapshots([older, latest], now=now)
        self.assertEqual(planner.forecast_end(merged), local(2026, 9, 29, 0).astimezone(UTC))
        by_time = {planner.parse_iso(r["period_end"]): r["pv_estimate"] for r in merged}
        self.assertEqual(by_time[local(2026, 9, 28, 1).astimezone(UTC)], 2.0)  # newest wins
        self.assertEqual(by_time[local(2026, 9, 28, 12).astimezone(UTC)], 1.0)  # gap filled

    def test_fill_copies_previous_day_and_flags_estimates(self) -> None:
        now = local(2026, 9, 27, 20)
        rows = pv_rows(local(2026, 9, 27, 6), local(2026, 9, 28, 2), midday_kw)
        until = local(2026, 9, 29, 0).astimezone(UTC)
        filled = planner.fill_missing_pv(rows, now=now, tz=TZ, until=until)
        self.assertEqual(planner.forecast_end(filled), until)
        est = {planner.parse_iso(r["period_end"]): r["pv_estimate"] for r in filled if r.get("estimated")}
        self.assertEqual(est[local(2026, 9, 28, 12).astimezone(UTC)], 3.0)
        self.assertEqual(est[local(2026, 9, 28, 20).astimezone(UTC)], 0.0)
        self.assertNotIn(local(2026, 9, 28, 1).astimezone(UTC), est)  # real rows kept

    def test_complete_forecast_is_untouched(self) -> None:
        now = local(2026, 9, 27, 20)
        rows = pv_rows(local(2026, 9, 27, 6), local(2026, 9, 29, 2), midday_kw)
        until = local(2026, 9, 29, 0).astimezone(UTC)
        self.assertEqual(planner.fill_missing_pv(rows, now=now, tz=TZ, until=until), rows)

    def test_estimated_pv_reaches_tomorrow_timeline(self) -> None:
        now = local(2026, 9, 27, 21)
        rows = pv_rows(local(2026, 9, 27, 6), local(2026, 9, 28, 2), lambda t: 4.0 if 9 <= t.hour < 16 else 0.0)
        until = local(2026, 9, 29, 0).astimezone(UTC)
        filled = planner.fill_missing_pv(rows, now=now, tz=TZ, until=until)
        imports = agile_rows(now, 30, lambda t: 5.0 if t.astimezone(TZ).hour < 6 else 25.0)
        tomorrow = local(2026, 9, 28, 12)
        blind = planner.build_timeline(now=now, tz=TZ, import_rows=imports, export_rows=None,
                                       forecast_rows=rows, load_profile=None, load_fallback_kw=0.5,
                                       carbon_periods=None, horizon_end=until)
        seen = planner.build_timeline(now=now, tz=TZ, import_rows=imports, export_rows=None,
                                      forecast_rows=filled, load_profile=None, load_fallback_kw=0.5,
                                      carbon_periods=None, horizon_end=until)
        blind_pv = sum(s.pv_kwh for s in blind if s.start.astimezone(TZ).date() == tomorrow.date())
        seen_pv = sum(s.pv_kwh for s in seen if s.start.astimezone(TZ).date() == tomorrow.date())
        self.assertLess(blind_pv, 1.0)
        self.assertGreater(seen_pv, 20.0)


if __name__ == "__main__":
    unittest.main()
