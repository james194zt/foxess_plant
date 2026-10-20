"""Rate evidence: what the supplier's API said about each negative-price half-hour (and each half-hour we
grid-charged in and re-checked), and what we did about it.

Users have been billed at a positive rate for half-hours the API showed as negative. This keeps a durable,
exportable record per half-hour so it can be sent to the supplier (``kind``: "negative", or "charge" for a
positive-price half-hour recorded by the rate check that runs while grid charging):

- ``api.first``: the exact rate row the API returned the first time the half-hour was negative (verbatim),
  with the request it came from: URL (the API key is never in it), when we asked, HTTP status and the
  supplier's own ``Date`` header.
- ``api.confirmations`` / ``api.last_confirmed_at``: later fetches that returned the same value.
- ``api.revisions``: every later fetch that returned a DIFFERENT value for that half-hour (also kept when the
  new value is positive) — a quiet revision is exactly what a dispute needs.
- ``actions``: what Fox Plant did and when (the Force Charge slot written to the inverter, SmartCharge's
  negative-price decision).
- ``import_kwh``: grid import across the half-hour, per source: ``smart_meter`` (the meter's own import
  register via Glow — the reading the bill is based on) and ``inverter`` (its lifetime grid counter).
  The meter's PRICE is deliberately not recorded: on Agile the meter isn't sent the half-hourly prices, so
  the rate Glow / an IHD reads from it isn't the real price.

Stored in .storage (survives restarts); the newest MAX_RECORDS half-hours are kept.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
MAX_RECORDS = 2000
MAX_ACTIONS = 20
MAX_REVISIONS = 50


def _utc(value: Any) -> datetime | None:
    parsed = dt_util.parse_datetime(str(value)) if value else None
    return dt_util.as_utc(parsed) if parsed else None


def _key(value: Any) -> str | None:
    when = _utc(value)
    return when.isoformat() if when else None


def _price(row: dict[str, Any]) -> float | None:
    try:
        return float(row.get("value_inc_vat"))
    except (TypeError, ValueError):
        return None


class PlungeEvidenceLog:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"foxess_plant.plunge_evidence.{entry_id}")
        self.records: dict[str, dict[str, Any]] = {}
        self._loaded = False

    async def async_load(self) -> None:
        if not self._loaded:
            data = await self._store.async_load() or {}
            self.records = dict(data.get("records") or {})
            self._loaded = True

    async def _async_save(self) -> None:
        if len(self.records) > MAX_RECORDS:
            for key in sorted(self.records)[: len(self.records) - MAX_RECORDS]:
                del self.records[key]
        await self._store.async_save({"records": self.records})

    # --- What the API said -----------------------------------------------------------------------------

    async def async_note_rates(
        self,
        rows: list[dict[str, Any]],
        request: dict[str, Any] | None,
        *,
        seen_at: datetime | None = None,
        track_all: bool = False,
    ) -> int:
        """Record negative half-hours from one unit-rates fetch, and any change to ones already recorded.

        ``track_all``: record these half-hours whatever the price (the rate check while grid charging).
        Returns how many records were created or changed.
        """
        await self.async_load()
        seen = (seen_at or dt_util.utcnow()).isoformat()
        request = dict(request or {})
        changed = 0
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            key = _key(row.get("valid_from"))
            price = _price(row)
            if key is None or price is None:
                continue
            record = self.records.get(key)
            if record is None:
                if price > 0 and not track_all:
                    continue
                self.records[key] = {
                    "kind": "negative" if price <= 0 else "charge",
                    "slot_start": key,
                    "slot_end": _key(row.get("valid_to")),
                    "tariff_code": request.get("tariff_code"),
                    "product_code": request.get("product_code"),
                    "mpan": request.get("mpan"),
                    "api": {
                        "first": {"seen_at": seen, "row": dict(row), "request": request},
                        "latest_value_inc_vat": price,
                        "last_confirmed_at": seen,
                        "confirmations": 1,
                        "revisions": [],
                    },
                    "actions": [],
                    "import_kwh": {},
                    "import_counters": {},
                }
                changed += 1
                continue
            api = record["api"]
            if price == api.get("latest_value_inc_vat"):
                api["last_confirmed_at"] = seen
                api["confirmations"] = int(api.get("confirmations") or 0) + 1
                changed += 1
            else:
                api["revisions"] = (api.get("revisions") or [])[-(MAX_REVISIONS - 1) :] + [
                    {"seen_at": seen, "row": dict(row), "request": request}
                ]
                api["latest_value_inc_vat"] = price
                api["last_confirmed_at"] = seen
                changed += 1
                _LOGGER.warning(
                    "Supplier API changed the %s rate from %s to %sp/kWh (was negative when first seen)",
                    key,
                    api["first"]["row"].get("value_inc_vat"),
                    price,
                )
        if changed:
            await self._async_save()
        return changed

    # --- What we did -----------------------------------------------------------------------------------

    async def async_note_action(
        self, start_utc: Any, end_utc: Any, what: str, *, details: dict[str, Any] | None = None
    ) -> None:
        """Attach an action to every recorded negative half-hour it covers (once per distinct text)."""
        await self.async_load()
        start, end = _utc(start_utc), _utc(end_utc)
        if start is None or end is None:
            return
        at = dt_util.utcnow().isoformat()
        changed = False
        for record in self.records.values():
            slot_start, slot_end = _utc(record["slot_start"]), _utc(record.get("slot_end"))
            if slot_start is None or slot_end is None or not (start < slot_end and slot_start < end):
                continue
            actions = record.setdefault("actions", [])
            if any(a.get("what") == what for a in actions):
                continue
            actions.append({"at": at, "what": what, **({"details": details} if details else {})})
            del actions[:-MAX_ACTIONS]
            changed = True
        if changed:
            await self._async_save()

    # --- What happened during the half-hour -------------------------------------------------------------

    async def async_note_half_hour(self, now: datetime, *, counters: dict[str, float | None]) -> None:
        """At each half-hour boundary: import counters (per source) for the half-hour starting and ending."""
        await self.async_load()
        now = dt_util.as_utc(now)
        at = now.isoformat()
        changed = False
        for record in self.records.values():
            start, end = _utc(record["slot_start"]), _utc(record.get("slot_end"))
            if start is None or end is None:
                continue
            readings = record.setdefault("import_counters", {})
            results = record.get("import_kwh")
            if not isinstance(results, dict):
                results = record["import_kwh"] = {}
            for source, value in counters.items():
                if value is None:
                    continue
                reading = readings.setdefault(source, {})
                if start <= now < end and "start_kwh" not in reading:
                    reading.update(start_kwh=value, start_at=at)
                    changed = True
                elif end <= now < end + timedelta(minutes=30) and "start_kwh" in reading and "end_kwh" not in reading:
                    reading.update(end_kwh=value, end_at=at)
                    delta = value - float(reading["start_kwh"])
                    results[source] = round(delta, 3) if delta >= 0 else None
                    changed = True
        if changed:
            await self._async_save()

    # --- Output ---------------------------------------------------------------------------------------

    def newest_first(self) -> list[dict[str, Any]]:
        return [self.records[k] for k in sorted(self.records, reverse=True)]


CSV_COLUMNS = (
    "kind",
    "slot_start_utc",
    "slot_end_utc",
    "tariff_code",
    "mpan",
    "api_first_value_inc_vat_p",
    "api_first_value_exc_vat_p",
    "api_first_seen_at_utc",
    "api_first_request_url",
    "api_first_server_date",
    "api_latest_value_inc_vat_p",
    "api_last_confirmed_at_utc",
    "api_confirmations",
    "api_revisions",
    "fox_plant_actions",
    "grid_import_kwh_smart_meter",
    "grid_import_kwh_inverter",
)


def to_csv(records: list[dict[str, Any]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(CSV_COLUMNS)
    for r in records:
        api = r.get("api") or {}
        first = api.get("first") or {}
        row = first.get("row") or {}
        request = first.get("request") or {}
        revisions = "; ".join(
            f"{rev.get('seen_at')}: {(rev.get('row') or {}).get('value_inc_vat')}p" for rev in api.get("revisions") or []
        )
        actions = "; ".join(f"{a.get('at')}: {a.get('what')}" for a in r.get("actions") or [])
        imported = r.get("import_kwh") if isinstance(r.get("import_kwh"), dict) else {}
        writer.writerow(
            [
                r.get("kind") or "negative",
                r.get("slot_start"),
                r.get("slot_end"),
                r.get("tariff_code"),
                r.get("mpan"),
                row.get("value_inc_vat"),
                row.get("value_exc_vat"),
                first.get("seen_at"),
                request.get("url"),
                request.get("server_date"),
                api.get("latest_value_inc_vat"),
                api.get("last_confirmed_at"),
                api.get("confirmations"),
                revisions,
                actions,
                imported.get("smart_meter"),
                imported.get("inverter"),
            ]
        )
    return out.getvalue()
