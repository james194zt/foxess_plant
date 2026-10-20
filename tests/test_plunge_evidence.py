"""Plunge evidence: what the Octopus API said about each negative half-hour, kept verbatim with the request."""

import csv
import io
from datetime import datetime, timezone

import pytest

from custom_components.foxess_plant.plunge_evidence import PlungeEvidenceLog, to_csv

REQUEST = {
    "url": "https://api.octopus.energy/v1/products/AGILE-24-10-01/electricity-tariffs/E-1R-AGILE-24-10-01-C/standard-unit-rates/?period_from=2026-10-20T10%3A00%3A00Z",
    "requested_at": "2026-10-20T12:00:01+00:00",
    "http_status": 200,
    "server_date": "Mon, 20 Oct 2026 12:00:01 GMT",
    "product_code": "AGILE-24-10-01",
    "tariff_code": "E-1R-AGILE-24-10-01-C",
    "mpan": "1900000000000",
}


def _row(start: str, end: str, inc: float) -> dict:
    return {"value_exc_vat": round(inc / 1.05, 4), "value_inc_vat": inc, "valid_from": start, "valid_to": end,
            "payment_method": None}


NEG = _row("2026-10-20T13:00:00Z", "2026-10-20T13:30:00Z", -2.1)
POS = _row("2026-10-20T13:30:00Z", "2026-10-20T14:00:00Z", 12.0)
T0 = datetime(2026, 10, 20, 12, 0, 1, tzinfo=timezone.utc)
KEY = "2026-10-20T13:00:00+00:00"


@pytest.mark.asyncio
async def test_records_negative_half_hours_verbatim_with_the_request(hass, hass_storage) -> None:
    log = PlungeEvidenceLog(hass, "e1")
    await log.async_note_rates([NEG, POS], REQUEST, seen_at=T0)

    assert list(log.records) == [KEY]  # positive half-hours aren't recorded
    first = log.records[KEY]["api"]["first"]
    assert first["row"] == NEG  # exactly what the API returned
    assert first["request"]["server_date"] == "Mon, 20 Oct 2026 12:00:01 GMT"
    assert "api_key" not in first["request"]["url"].lower()
    assert hass_storage["foxess_plant.plunge_evidence.e1"]["data"]["records"][KEY]["tariff_code"] == REQUEST["tariff_code"]


@pytest.mark.asyncio
async def test_same_value_counts_as_confirmation_and_a_change_is_kept_as_a_revision(hass, hass_storage) -> None:
    log = PlungeEvidenceLog(hass, "e1")
    await log.async_note_rates([NEG], REQUEST, seen_at=T0)
    await log.async_note_rates([NEG], REQUEST, seen_at=datetime(2026, 10, 20, 12, 30, tzinfo=timezone.utc))
    api = log.records[KEY]["api"]
    assert api["confirmations"] == 2 and api["revisions"] == []

    revised = {**NEG, "value_inc_vat": 15.3, "value_exc_vat": 14.57}
    await log.async_note_rates([revised], REQUEST, seen_at=datetime(2026, 10, 20, 14, 0, tzinfo=timezone.utc))
    api = log.records[KEY]["api"]
    assert api["latest_value_inc_vat"] == 15.3
    assert api["revisions"][0]["row"]["value_inc_vat"] == 15.3
    assert api["first"]["row"]["value_inc_vat"] == -2.1  # the original answer is never overwritten


@pytest.mark.asyncio
async def test_actions_attach_only_to_negative_half_hours_they_cover(hass, hass_storage) -> None:
    log = PlungeEvidenceLog(hass, "e1")
    await log.async_note_rates([NEG, _row("2026-10-20T15:00:00Z", "2026-10-20T15:30:00Z", -1.0)], REQUEST, seen_at=T0)
    what = "Force Charge slot on the inverter: 14:00-14:30 to 100% at 3600 W"
    await log.async_note_action("2026-10-20T13:00:00+00:00", "2026-10-20T13:30:00+00:00", what)
    await log.async_note_action("2026-10-20T13:00:00+00:00", "2026-10-20T13:30:00+00:00", what)  # no duplicate

    assert [a["what"] for a in log.records[KEY]["actions"]] == [what]
    assert log.records["2026-10-20T15:00:00+00:00"]["actions"] == []


@pytest.mark.asyncio
async def test_meter_rate_and_grid_import_across_the_half_hour(hass, hass_storage) -> None:
    log = PlungeEvidenceLog(hass, "e1")
    await log.async_note_rates([NEG], REQUEST, seen_at=T0)
    meter = {"meter_p_per_kwh": -2.1, "api_p_per_kwh": -2.1, "entity_id": "sensor.glow_import_rate"}

    await log.async_note_half_hour(datetime(2026, 10, 20, 13, 0, 5, tzinfo=timezone.utc), meter=meter, import_counter_kwh=1000.0)
    await log.async_note_half_hour(datetime(2026, 10, 20, 13, 3, 5, tzinfo=timezone.utc), meter=meter, import_counter_kwh=1000.3)
    await log.async_note_half_hour(datetime(2026, 10, 20, 13, 30, 5, tzinfo=timezone.utc), meter=None, import_counter_kwh=1001.8)

    record = log.records[KEY]
    assert record["import_kwh"] == 1.8  # from the reading at the start, not the follow-up
    assert [m["meter_p_per_kwh"] for m in record["meter"]] == [-2.1, -2.1]


@pytest.mark.asyncio
async def test_rate_check_while_charging_records_positive_half_hours_too(hass, hass_storage) -> None:
    log = PlungeEvidenceLog(hass, "e1")
    await log.async_note_rates([POS], REQUEST, seen_at=T0)
    assert log.records == {}  # a normal fetch only records negative half-hours
    await log.async_note_rates([POS], {**REQUEST, "purpose": "rate check"}, seen_at=T0, track_all=True)
    record = log.records["2026-10-20T13:30:00+00:00"]
    assert record["kind"] == "charge"
    assert record["api"]["first"]["request"]["purpose"] == "rate check"


@pytest.mark.asyncio
async def test_survives_a_restart(hass, hass_storage) -> None:
    await PlungeEvidenceLog(hass, "e1").async_note_rates([NEG], REQUEST, seen_at=T0)
    log = PlungeEvidenceLog(hass, "e1")
    await log.async_load()
    assert log.records[KEY]["api"]["first"]["row"] == NEG


@pytest.mark.asyncio
async def test_csv_has_the_evidence_columns(hass, hass_storage) -> None:
    log = PlungeEvidenceLog(hass, "e1")
    await log.async_note_rates([NEG], REQUEST, seen_at=T0)
    rows = list(csv.DictReader(io.StringIO(to_csv(log.newest_first()))))
    assert rows[0]["api_first_value_inc_vat_p"] == "-2.1"
    assert rows[0]["api_first_server_date"] == REQUEST["server_date"]
    assert rows[0]["api_first_request_url"] == REQUEST["url"]
    assert rows[0]["tariff_code"] == REQUEST["tariff_code"]
