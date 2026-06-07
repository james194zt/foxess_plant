"""Octopus tariff discovery, schedule building, and live rate resolution."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from .octopus_api import OctopusApiClient, OctopusApiError
from .tariff_schedule import TARIFF_BAND_COUNT, TARIFF_HOUR_COUNT, TariffBandConfig, TariffScheduleConfig

_LOGGER = logging.getLogger(__name__)

OCTOPUS_PROVIDER = "octopus"
OCTOPUS_SOURCE_NATIVE = "native"
OCTOPUS_SOURCE_ENTITY = "entity"

TARIFF_TYPE_AGILE = "agile"
TARIFF_TYPE_TRACKER = "tracker"
TARIFF_TYPE_GO = "go"
TARIFF_TYPE_ECONOMY7 = "economy7"
TARIFF_TYPE_FLAT = "flat"

UK_TZ = ZoneInfo("Europe/London")


@dataclass
class OctopusMeterSummary:
    mpan: str
    serial: str | None
    is_export: bool
    tariff_code: str | None
    product_code: str | None
    display_name: str


@dataclass
class OctopusTariffSnapshot:
    tariff_type: str
    import_meter: OctopusMeterSummary | None = None
    export_meter: OctopusMeterSummary | None = None
    import_rates: list[dict[str, Any]] = field(default_factory=list)
    export_rates: list[dict[str, Any]] = field(default_factory=list)
    import_standing_p_per_day: float | None = None
    export_standing_p_per_day: float | None = None
    schedule: TariffScheduleConfig | None = None
    current_import_p_per_kwh: float | None = None
    current_export_p_per_kwh: float | None = None
    last_fetch_at: str | None = None
    last_error: str | None = None

    def to_cache_dict(self) -> dict[str, Any]:
        return {
            "tariff_type": self.tariff_type,
            "import_meter": _meter_to_dict(self.import_meter),
            "export_meter": _meter_to_dict(self.export_meter),
            "import_tariff_code": self.import_meter.tariff_code if self.import_meter else None,
            "export_tariff_code": self.export_meter.tariff_code if self.export_meter else None,
            "import_product_code": self.import_meter.product_code if self.import_meter else None,
            "export_product_code": self.export_meter.product_code if self.export_meter else None,
            "import_rates_count": len(self.import_rates),
            "export_rates_count": len(self.export_rates),
            "import_standing_p_per_day": self.import_standing_p_per_day,
            "export_standing_p_per_day": self.export_standing_p_per_day,
            "schedule": self.schedule.to_dict() if self.schedule else None,
            "current_import_p_per_kwh": self.current_import_p_per_kwh,
            "current_export_p_per_kwh": self.current_export_p_per_kwh,
            "last_fetch_at": self.last_fetch_at,
            "last_error": self.last_error,
        }


def _meter_to_dict(meter: OctopusMeterSummary | None) -> dict[str, Any] | None:
    if meter is None:
        return None
    return {
        "mpan": meter.mpan,
        "serial": meter.serial,
        "is_export": meter.is_export,
        "tariff_code": meter.tariff_code,
        "product_code": meter.product_code,
        "display_name": meter.display_name,
    }


def classify_tariff_code(tariff_code: str | None) -> str:
    code = str(tariff_code or "").upper()
    if "AGILE" in code:
        return TARIFF_TYPE_AGILE
    if "TRACKER" in code:
        return TARIFF_TYPE_TRACKER
    if "GO-" in code or "GO-VAR" in code or "-GO-" in code:
        return TARIFF_TYPE_GO
    if code.startswith("E-2R"):
        return TARIFF_TYPE_ECONOMY7
    return TARIFF_TYPE_FLAT


def is_variable_tariff_type(tariff_type: str) -> bool:
    return tariff_type in (TARIFF_TYPE_AGILE, TARIFF_TYPE_TRACKER)


def list_account_meters(account: dict[str, Any]) -> tuple[list[OctopusMeterSummary], list[OctopusMeterSummary]]:
    """Split import and export electricity meter points from an account payload."""
    import_meters: list[OctopusMeterSummary] = []
    export_meters: list[OctopusMeterSummary] = []
    for prop in account.get("properties") or []:
        if not isinstance(prop, dict):
            continue
        for mp in prop.get("electricity_meter_points") or []:
            if not isinstance(mp, dict):
                continue
            mpan = str(mp.get("mpan") or "").strip()
            if not mpan:
                continue
            agreement = _active_agreement(mp.get("agreements") or [])
            tariff_code = str(agreement.get("tariff_code") or "").strip() if agreement else None
            serial = None
            meters = mp.get("meters") or []
            if meters and isinstance(meters[0], dict):
                serial = str(meters[0].get("serial_number") or "").strip() or None
            is_export = bool(mp.get("is_export"))
            label_bits = [mpan[-4:] if len(mpan) >= 4 else mpan]
            if tariff_code:
                label_bits.append(tariff_code)
            summary = OctopusMeterSummary(
                mpan=mpan,
                serial=serial,
                is_export=is_export,
                tariff_code=tariff_code or None,
                product_code=None,
                display_name=" · ".join(label_bits),
            )
            if is_export:
                export_meters.append(summary)
            else:
                import_meters.append(summary)
    return import_meters, export_meters


def _active_agreement(agreements: list[Any]) -> dict[str, Any] | None:
    now = dt_util.utcnow()
    active: dict[str, Any] | None = None
    for raw in agreements:
        if not isinstance(raw, dict):
            continue
        tariff_code = raw.get("tariff_code")
        if not tariff_code:
            continue
        valid_from = _parse_api_dt(raw.get("valid_from"))
        valid_to = _parse_api_dt(raw.get("valid_to"))
        if valid_from is None:
            continue
        if valid_from <= now and (valid_to is None or valid_to > now):
            return raw
        if active is None:
            active = raw
    return active


def _parse_api_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        return None
    return dt_util.as_utc(parsed)


async def find_product_for_tariff(client: OctopusApiClient, tariff_code: str) -> str | None:
    code = str(tariff_code or "").strip()
    if not code:
        return None
    products = await client.get_products()
    for product in products:
        product_code = str(product.get("code") or "")
        if not product_code:
            continue
        for key in ("single_register_electricity_tariffs", "dual_register_electricity_tariffs"):
            tariffs = product.get(key) or []
            if not isinstance(tariffs, list):
                continue
            for item in tariffs:
                if isinstance(item, dict) and str(item.get("code") or "") == code:
                    return product_code
    return None


def _rate_value_inc_vat(row: dict[str, Any]) -> float | None:
    try:
        return float(row.get("value_inc_vat"))
    except (TypeError, ValueError):
        return None


def rate_at(when: datetime, rates: list[dict[str, Any]]) -> float | None:
    """Return the inc-VAT p/kWh rate active at ``when`` (UTC-aware)."""
    target = dt_util.as_utc(when)
    for row in rates:
        start = _parse_api_dt(row.get("valid_from"))
        end = _parse_api_dt(row.get("valid_to"))
        if start is None:
            continue
        if start <= target and (end is None or target < end):
            return _rate_value_inc_vat(row)
    return None


def standing_charge_at(when: datetime, rows: list[dict[str, Any]]) -> float | None:
    target = dt_util.as_utc(when)
    for row in rows:
        start = _parse_api_dt(row.get("valid_from"))
        end = _parse_api_dt(row.get("valid_to"))
        if start is None:
            continue
        if start <= target and (end is None or target < end):
            return _rate_value_inc_vat(row)
    return None


def build_schedule_from_rates(
    import_rates: list[dict[str, Any]],
    export_rates: list[dict[str, Any]] | None = None,
    *,
    sample_day: date | None = None,
) -> TariffScheduleConfig | None:
    """Map Octopus unit-rate windows onto the 24-block schedule editor."""
    if not import_rates:
        return None
    day = sample_day or dt_util.as_local(dt_util.now()).date()
    hour_pairs: list[tuple[float | None, float | None]] = []
    for hour in range(TARIFF_HOUR_COUNT):
        sample_local = datetime.combine(day, time(hour=hour, minute=30), tzinfo=UK_TZ)
        sample_utc = sample_local.astimezone(dt_util.UTC)
        import_p = rate_at(sample_utc, import_rates)
        export_p = rate_at(sample_utc, export_rates or []) if export_rates else None
        hour_pairs.append((import_p, export_p))

    unique: list[tuple[float | None, float | None]] = []
    hours: list[int] = []
    for pair in hour_pairs:
        if pair not in unique:
            if len(unique) >= TARIFF_BAND_COUNT:
                band_idx = 0
            else:
                unique.append(pair)
                band_idx = len(unique) - 1
        else:
            band_idx = unique.index(pair)
        hours.append(band_idx)

    bands: list[TariffBandConfig] = []
    for import_p, export_p in unique:
        bands.append(
            TariffBandConfig(
                import_p_per_kwh=float(import_p or 0),
                export_p_per_kwh=float(export_p or 0),
            )
        )
    while len(bands) < TARIFF_BAND_COUNT:
        bands.append(TariffBandConfig())
    return TariffScheduleConfig(hours=hours, bands=bands)


def next_octopus_poll_boundary(when: datetime | None = None, *, agile: bool) -> datetime:
    """Next poll instant: half-hour for Agile, hour boundary for fixed tariffs."""
    local = dt_util.as_local(when or dt_util.now())
    if agile:
        minute = local.minute
        if minute < 30:
            nxt = local.replace(minute=30, second=0, microsecond=0)
        else:
            nxt = local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return dt_util.as_utc(nxt)
    nxt = local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return dt_util.as_utc(nxt)


def _iso_period(dt: datetime) -> str:
    return dt_util.as_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


async def fetch_octopus_tariff_snapshot(
    client: OctopusApiClient,
    *,
    account_number: str,
    import_mpan: str | None = None,
    export_mpan: str | None = None,
) -> OctopusTariffSnapshot:
    account = await client.get_account(account_number)
    import_meters, export_meters = list_account_meters(account)
    if not import_meters:
        raise OctopusApiError("No import electricity meter found on this Octopus account")

    import_meter = _pick_meter(import_meters, import_mpan)
    export_meter = _pick_meter(export_meters, export_mpan) if export_meters else None

    if import_meter.tariff_code is None:
        raise OctopusApiError("Import meter has no active tariff agreement")

    import_product = await find_product_for_tariff(client, import_meter.tariff_code)
    if import_product is None:
        raise OctopusApiError(f"Could not find Octopus product for tariff {import_meter.tariff_code}")
    import_meter.product_code = import_product

    export_product = None
    if export_meter and export_meter.tariff_code:
        export_product = await find_product_for_tariff(client, export_meter.tariff_code)
        export_meter.product_code = export_product

    tariff_type = classify_tariff_code(import_meter.tariff_code)
    now = dt_util.utcnow()
    local_now = dt_util.as_local(now)
    period_from = _iso_period((local_now - timedelta(hours=2)).astimezone(dt_util.UTC))
    if is_variable_tariff_type(tariff_type):
        period_to = _iso_period((local_now + timedelta(hours=50)).astimezone(dt_util.UTC))
    else:
        period_to = _iso_period((local_now + timedelta(days=2)).astimezone(dt_util.UTC))

    import_rates = await client.get_unit_rates(
        import_product,
        import_meter.tariff_code,
        period_from=period_from,
        period_to=period_to,
    )
    export_rates: list[dict[str, Any]] = []
    if export_meter and export_meter.tariff_code and export_product:
        export_rates = await client.get_unit_rates(
            export_product,
            export_meter.tariff_code,
            period_from=period_from,
            period_to=period_to,
        )

    import_standing_rows = await client.get_standing_charges(
        import_product,
        import_meter.tariff_code,
        period_from=period_from,
        period_to=period_to,
    )
    import_standing = standing_charge_at(now, import_standing_rows)

    schedule = None
    if not is_variable_tariff_type(tariff_type):
        schedule = build_schedule_from_rates(import_rates, export_rates or None)

    snapshot = OctopusTariffSnapshot(
        tariff_type=tariff_type,
        import_meter=import_meter,
        export_meter=export_meter,
        import_rates=import_rates,
        export_rates=export_rates,
        import_standing_p_per_day=import_standing,
        current_import_p_per_kwh=rate_at(now, import_rates),
        current_export_p_per_kwh=rate_at(now, export_rates) if export_rates else None,
        schedule=schedule,
        last_fetch_at=now.isoformat(),
        last_error=None,
    )
    return snapshot


def _pick_meter(meters: list[OctopusMeterSummary], mpan: str | None) -> OctopusMeterSummary:
    if mpan:
        target = str(mpan).strip()
        for meter in meters:
            if meter.mpan == target:
                return meter
        raise OctopusApiError(f"Meter MPAN {target} was not found on this account")
    if len(meters) == 1:
        return meters[0]
    raise OctopusApiError(
        "Multiple electricity meters found — select an import MPAN in Octopus settings"
    )


async def test_octopus_connection(
    client: OctopusApiClient,
    *,
    account_number: str,
) -> dict[str, Any]:
    account = await client.get_account(account_number)
    import_meters, export_meters = list_account_meters(account)
    return {
        "account_number": account_number.strip().upper(),
        "import_meters": [_meter_to_dict(m) for m in import_meters],
        "export_meters": [_meter_to_dict(m) for m in export_meters],
        "property_count": len(account.get("properties") or []),
    }
