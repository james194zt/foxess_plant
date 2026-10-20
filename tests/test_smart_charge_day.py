"""SmartCharge day view: planned vs actual per half-hour."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util

from custom_components.foxess_plant.smart_charge_day import build_day, day_slots, plan_slot_rows, utc_key

LONDON = ZoneInfo("Europe/London")
UTC = timezone.utc


@pytest.fixture(autouse=True)
def london():
    old = dt_util.get_default_time_zone()
    dt_util.set_default_time_zone(LONDON)
    yield
    dt_util.set_default_time_zone(old)


def local(d, h, m=0):
    return datetime(2026, 10, d, h, m, tzinfo=LONDON)


def test_plan_rows_skip_half_hours_already_started():
    now = local(21, 2, 10)
    plan = [
        {"start_utc": utc_key(local(21, 2, 10)), "end_utc": utc_key(local(21, 2, 30)), "action": "charge"},  # running
        {"start_utc": utc_key(local(21, 2, 30)), "end_utc": utc_key(local(21, 3, 0)), "action": "charge",
         "soc_end_pct": 40.0, "import_p_per_kwh": 18.05},
    ]
    rows = plan_slot_rows(plan, now, built_at="x")
    assert [r["start_utc"] for r in rows] == [utc_key(local(21, 2, 30))]
    assert rows[0]["soc_end_pct"] == 40.0 and rows[0]["import_p_per_kwh"] == 18.05


def test_clock_change_day_has_50_half_hours():
    assert len(day_slots(date(2026, 10, 25))) == 50
    assert len(day_slots(date(2026, 10, 21))) == 48


def _kwh(table):
    def kwh_in(key, s_ms, e_ms):
        start = datetime.fromtimestamp(s_ms / 1000, tz=UTC).astimezone(LONDON).strftime("%H:%M")
        return table.get(start, {}).get(key, 0.0)
    return kwh_in


def test_planned_vs_actual():
    day = date(2026, 10, 21)
    now = local(21, 4, 15)
    stored = [
        {"start_utc": utc_key(local(21, 3, 0)), "action": "charge", "planned_import_kwh": 1.8,
         "soc_start_pct": 30.0, "soc_end_pct": 50.0, "import_p_per_kwh": 18.05},
    ]
    # Older day-plan audit event (before the stored history existed): 02:00 and 02:30 were charge slots
    audit = [{"ts": utc_key(local(20, 21, 0)), "payload": {"slots": [
        {"start_utc": utc_key(local(21, 2, 0)), "action": "charge", "planned_import_kwh": 1.8},
        {"start_utc": utc_key(local(21, 2, 30)), "action": "charge", "planned_import_kwh": 1.8},
    ]}}]
    kwh = _kwh({
        "02:00": {"battery_charge": 1.6, "grid_import": 1.75},
        "03:00": {"battery_charge": 1.7, "grid_import": 1.8},
        "01:00": {"battery_charge": 0.0, "grid_import": 0.05, "grid_export": 0.05, "battery_discharge": 0.2},  # CT noise
        "00:00": {"battery_discharge": 0.5, "grid_export": 0.4},
    })
    soc = [(local(21, 2, 0).timestamp() * 1000, 15.0), (local(21, 3, 0).timestamp() * 1000, 33.0),
           (local(21, 3, 30).timestamp() * 1000, 52.0)]
    out = build_day(day=day, now=now, plan_rows=stored, audit_events=audit, soc_points=soc, kwh_in=kwh)
    by = {s["start"]: s for s in out["slots"]}
    assert by["02:00"]["plan"]["action"] == "charge"  # from the audit fallback
    assert by["01:00"]["plan"]["action"] == "idle"  # audit lists only charge/export half-hours
    assert by["03:00"]["plan"]["soc_end_pct"] == 50.0  # from the stored history
    assert by["02:00"]["actual"]["action"] == "charge" and by["02:00"]["actual"]["grid_charge_kwh"] == 1.6
    assert by["01:00"]["actual"]["action"] == "idle"  # 50 Wh of CT noise isn't an export
    assert by["00:00"]["actual"]["action"] == "export"
    assert by["03:00"]["actual"]["soc_start_pct"] == 33.0 and by["03:00"]["actual"]["soc_end_pct"] == 52.0
    assert by["05:00"]["actual"] is None and by["05:00"]["plan"] is None  # future, nothing stored
    assert out["plan_source"] == "mixed"
    s = out["summary"]
    assert s["actual_charge_kwh"] == pytest.approx(3.3)
    assert s["planned_charge_kwh"] == pytest.approx(5.4)
    assert s["charge_cost_p"] == pytest.approx(1.7 * 18.05, abs=0.1)  # only 03:00 has a known price
    assert s["soc_min_pct"] == 15.0 and s["soc_max_pct"] == 52.0


def test_no_history_at_all_is_empty_not_an_error():
    out = build_day(day=date(2026, 10, 21), now=local(21, 12), plan_rows=[], audit_events=[], soc_points=[],
                    kwh_in=lambda *a: None)
    assert out["plan_source"] is None
    assert all(s["plan"] is None for s in out["slots"])
    assert out["slots"][0]["actual"]["action"] == "idle" and out["slots"][0]["actual"]["grid_charge_kwh"] is None
