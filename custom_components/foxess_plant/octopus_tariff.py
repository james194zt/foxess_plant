"""Octopus tariff discovery, schedule building, and live rate resolution."""

from __future__ import annotations

import logging
import re
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

# E-1R-{product}-{gsp} or E-2R-{product}-{gsp} (gsp = A–P regional group)
_TARIFF_PRODUCT_RE = re.compile(r"^[EG]-[12]R-(.+)-([A-P])$", re.IGNORECASE)

_TARIFF_REGION_KEYS = (
    "single_register_electricity_tariffs",
    "dual_register_electricity_tariffs",
    "single_register_gas_tariffs",
)


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


def is_tracker_tariff_type(tariff_type: str | None) -> bool:
    return str(tariff_type or "") == TARIFF_TYPE_TRACKER


def tariff_looks_like_export(tariff_code: str | None) -> bool:
    """True when a tariff code is an Outgoing / SEG / Flux export product."""
    code = str(tariff_code or "").upper()
    if not code:
        return False
    # Import Flux / Agile must not be treated as export.
    if "IMPORT" in code and "EXPORT" not in code and "OUTGOING" not in code:
        return False
    return any(
        marker in code
        for marker in (
            "OUTGOING",
            "EXPORT",
            "-SEG-",
            "SEG-HH",
            "E-1R-SEG",
            "FLUX-EXPORT",
            "INTELLI-FLUX",
        )
    )


def _agreement_currently_valid(agreement: dict[str, Any], *, now: datetime | None = None) -> bool:
    now = now or dt_util.utcnow()
    valid_from = _parse_api_dt(agreement.get("valid_from"))
    valid_to = _parse_api_dt(agreement.get("valid_to"))
    if valid_from is None:
        return False
    return valid_from <= now and (valid_to is None or valid_to > now)


def _pick_serial_from_meters(meters: list[Any], *, now: datetime | None = None) -> str | None:
    """Prefer an active meter serial (skip closed meters when active_to is set)."""
    now = now or dt_util.utcnow()
    fallback: str | None = None
    for raw in meters or []:
        if not isinstance(raw, dict):
            continue
        serial = str(
            raw.get("serial_number") or raw.get("serialNumber") or raw.get("serial") or ""
        ).strip()
        if not serial:
            continue
        active_to = _parse_api_dt(raw.get("active_to") or raw.get("activeTo"))
        if active_to is not None and active_to <= now:
            if fallback is None:
                fallback = serial
            continue
        return serial
    return fallback


def _export_agreement(agreements: list[Any], *, now: datetime | None = None) -> dict[str, Any] | None:
    """Prefer a currently valid export tariff agreement on the meter point."""
    now = now or dt_util.utcnow()
    fallback: dict[str, Any] | None = None
    for raw in agreements or []:
        if not isinstance(raw, dict):
            continue
        if not tariff_looks_like_export(raw.get("tariff_code")):
            continue
        if _agreement_currently_valid(raw, now=now):
            return raw
        if fallback is None:
            fallback = raw
    return fallback


def _meter_looks_like_export(meter_point: dict[str, Any], tariff_code: str | None) -> bool:
    """True for SEG / Outgoing export MPAN points (REST flag, GraphQL direction, or tariff)."""
    if bool(meter_point.get("is_export")):
        return True
    if str(meter_point.get("direction") or "").upper() == "EXPORT":
        return True
    if tariff_looks_like_export(tariff_code):
        return True
    return _export_agreement(meter_point.get("agreements") or []) is not None


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
            agreements = mp.get("agreements") or []
            active = _active_agreement(agreements)
            export_agr = _export_agreement(agreements)
            is_export = _meter_looks_like_export(
                mp, (export_agr or active or {}).get("tariff_code") if (export_agr or active) else None
            )
            if is_export:
                agreement = export_agr or active
            else:
                agreement = active
            tariff_code = str(agreement.get("tariff_code") or "").strip() if agreement else None
            serial = _pick_serial_from_meters(mp.get("meters") or [])
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


def merge_export_meters(
    rest_meters: list[OctopusMeterSummary],
    gql_meters: list[OctopusMeterSummary],
) -> list[OctopusMeterSummary]:
    """Fill missing REST export serials from GraphQL and add GraphQL-only export MPANs."""
    from dataclasses import replace

    if not rest_meters:
        return list(gql_meters)
    by_mpan = {m.mpan: m for m in gql_meters}
    out: list[OctopusMeterSummary] = []
    seen: set[str] = set()
    for meter in rest_meters:
        seen.add(meter.mpan)
        alt = by_mpan.get(meter.mpan)
        if meter.serial or alt is None or not alt.serial:
            out.append(meter)
            continue
        out.append(
            replace(
                meter,
                serial=alt.serial,
                tariff_code=meter.tariff_code or alt.tariff_code,
                display_name=meter.display_name or alt.display_name,
            )
        )
    for meter in gql_meters:
        if meter.mpan not in seen:
            out.append(meter)
    return out


async def enrich_export_meters_via_graphql(
    client: OctopusApiClient,
    account_number: str,
    export_meters: list[OctopusMeterSummary],
) -> list[OctopusMeterSummary]:
    """Use GraphQL EXPORT direction when REST omits is_export or meter serials."""
    needs_enrich = (not export_meters) or any(not m.serial for m in export_meters)
    if not needs_enrich:
        return export_meters
    try:
        from .octopus_graphql import OctopusGraphqlClient, OctopusGraphqlError
    except ImportError:
        return export_meters
    gql = OctopusGraphqlClient(client._hass, api_key=client._api_key)
    try:
        gql_account = await gql.fetch_account_as_rest(account_number)
    except OctopusGraphqlError as err:
        _LOGGER.debug("GraphQL export meter enrich failed: %s", err)
        return export_meters
    _, gql_export = list_account_meters(gql_account)
    if not gql_export:
        return export_meters
    merged = merge_export_meters(export_meters, gql_export)
    if len(merged) != len(export_meters) or any(
        (a.serial != b.serial) for a, b in zip(export_meters, merged)
    ):
        _LOGGER.info(
            "Octopus export meters enriched via GraphQL (%s → %s, serials=%s)",
            len(export_meters),
            len(merged),
            sum(1 for m in merged if m.serial),
        )
    return merged


def resolve_meter_for_consumption(
    octopus_cache: dict[str, Any],
    *,
    export: bool = False,
) -> dict[str, Any]:
    """Pick MPAN/serial for consumption polls from singular meter or meters list."""
    prefix = "export" if export else "import"
    meter = octopus_cache.get(f"{prefix}_meter")
    if isinstance(meter, dict):
        mpan = str(meter.get("mpan") or "").strip()
        serial = str(meter.get("serial") or "").strip()
        if mpan and serial:
            return meter
    for row in octopus_cache.get(f"{prefix}_meters") or []:
        if not isinstance(row, dict):
            continue
        mpan = str(row.get("mpan") or "").strip()
        serial = str(row.get("serial") or "").strip()
        if mpan and serial:
            return row
    if isinstance(meter, dict) and str(meter.get("mpan") or "").strip():
        return meter
    return {}


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
    code = str(tariff_code or "").strip().upper()
    if not code:
        return None

    derived = product_code_from_tariff_code(code)
    if derived:
        return derived

    products = await client.get_products()
    for product in products:
        product_code = str(product.get("code") or "")
        if not product_code:
            continue
        for tcode in _tariff_codes_in_product(product):
            if tcode.upper() == code:
                return product_code
        try:
            detail = await client.get_product(product_code)
        except OctopusApiError:
            continue
        for tcode in _tariff_codes_in_product(detail):
            if tcode.upper() == code:
                return product_code
    return None


def product_code_from_tariff_code(tariff_code: str) -> str | None:
    """Derive Octopus product code from a standard import/export tariff code."""
    code = str(tariff_code or "").strip().upper()
    match = _TARIFF_PRODUCT_RE.match(code)
    if not match:
        return None
    return match.group(1)


def _tariff_codes_in_product(product: dict[str, Any]) -> list[str]:
    """Extract tariff codes from a product list or detail payload."""
    codes: list[str] = []
    for key in _TARIFF_REGION_KEYS:
        regional = product.get(key)
        if not isinstance(regional, dict):
            continue
        for payment_methods in regional.values():
            if not isinstance(payment_methods, dict):
                continue
            for tariff in payment_methods.values():
                if not isinstance(tariff, dict):
                    continue
                tcode = str(tariff.get("code") or "").strip()
                if tcode:
                    codes.append(tcode)
    return codes


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


def next_agile_poll_boundary(
    when: datetime | None = None,
    *,
    interval_minutes: int = 15,
) -> datetime:
    """Next Agile poll instant aligned to interval (default every 15 minutes)."""
    local = dt_util.as_local(when or dt_util.now())
    step = max(1, min(60, interval_minutes))
    minute = local.minute
    next_minute = ((minute // step) + 1) * step
    if next_minute >= 60:
        nxt = local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        nxt = local.replace(minute=next_minute, second=0, microsecond=0)
    return dt_util.as_utc(nxt)


def next_daily_smart_charge_plan_boundary(
    when: datetime | None = None,
    *,
    plan_time: str = "16:00",
) -> datetime:
    """Next daily SmartCharge plan boundary (default 16:00 UK local)."""
    local = dt_util.as_local(when or dt_util.now())
    try:
        hour_s, minute_s = plan_time.split(":", 1)
        hour = int(hour_s)
        minute = int(minute_s)
    except (TypeError, ValueError):
        hour, minute = 16, 0
    candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    return dt_util.as_utc(candidate)


def next_octopus_poll_boundary(
    when: datetime | None = None,
    *,
    agile: bool,
    interval_minutes: int = 15,
) -> datetime:
    """Next poll instant: Agile interval (default 15 min) or hour boundary for fixed tariffs."""
    if agile:
        return next_agile_poll_boundary(when, interval_minutes=interval_minutes)
    local = dt_util.as_local(when or dt_util.now())
    nxt = local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return dt_util.as_utc(nxt)


def _iso_period(dt: datetime) -> str:
    return dt_util.as_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick_meter(
    meters: list[OctopusMeterSummary],
    mpan: str | None,
    *,
    role: str = "import",
    allow_first: bool = False,
) -> OctopusMeterSummary:
    if mpan:
        target = str(mpan).strip()
        for meter in meters:
            if meter.mpan == target:
                return meter
        raise OctopusApiError(f"Meter MPAN {target} was not found on this account")
    if len(meters) == 1:
        return meters[0]
    if allow_first and meters:
        with_tariff = [m for m in meters if m.tariff_code]
        return (with_tariff or meters)[0]
    raise OctopusApiError(
        f"Multiple {role} electricity meters found — select an {role} MPAN in Octopus settings"
    )


async def fetch_octopus_tariff_snapshot(
    client: OctopusApiClient,
    *,
    account_number: str,
    import_mpan: str | None = None,
    export_mpan: str | None = None,
) -> OctopusTariffSnapshot:
    account = await client.get_account(account_number)
    import_meters, export_meters = list_account_meters(account)
    export_meters = await enrich_export_meters_via_graphql(client, account_number, export_meters)
    if not import_meters:
        raise OctopusApiError("No import electricity meter found on this Octopus account")

    import_meter = _pick_meter(import_meters, import_mpan, role="import")
    # Auto-pick when unset so a missing export MPAN never blocks import Agile rates.
    export_meter = (
        _pick_meter(export_meters, export_mpan, role="export", allow_first=True)
        if export_meters
        else None
    )

    if import_meter.tariff_code is None:
        raise OctopusApiError("Import meter has no active tariff agreement")

    import_product = await find_product_for_tariff(client, import_meter.tariff_code)
    if import_product is None:
        raise OctopusApiError(f"Could not find Octopus product for tariff {import_meter.tariff_code}")
    import_meter.product_code = import_product

    export_product = None
    # Soft warnings only when an export meter exists but rates cannot be loaded.
    # Accounts without SEG simply have no export rates — not an error.
    export_warning: str | None = None
    if export_meter is None:
        _LOGGER.info(
            "Octopus: no export/SEG meter on account %s — Outgoing rates unavailable",
            account_number.strip().upper(),
        )
    elif not export_meter.tariff_code:
        export_warning = f"Export meter {export_meter.mpan} has no active tariff agreement"
    else:
        export_product = await find_product_for_tariff(client, export_meter.tariff_code)
        export_meter.product_code = export_product
        if export_product is None:
            export_warning = (
                f"Could not resolve Octopus product for export tariff {export_meter.tariff_code}"
            )

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
        try:
            export_rates = await client.get_unit_rates(
                export_product,
                export_meter.tariff_code,
                period_from=period_from,
                period_to=period_to,
            )
        except OctopusApiError as err:
            export_warning = f"Export unit rates failed: {err}"
            _LOGGER.warning("Octopus export rates failed: %s", err)
        if not export_rates and not export_warning:
            export_warning = (
                f"Export tariff {export_meter.tariff_code} returned no unit rates for the window"
            )

    if export_warning:
        _LOGGER.info("Octopus export: %s", export_warning)

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
        last_error=export_warning,
    )
    return snapshot


async def test_octopus_connection(
    client: OctopusApiClient,
    *,
    account_number: str,
) -> dict[str, Any]:
    account = await client.get_account(account_number)
    import_meters, export_meters = list_account_meters(account)
    export_meters = await enrich_export_meters_via_graphql(client, account_number, export_meters)
    return {
        "account_number": account_number.strip().upper(),
        "import_meters": [_meter_to_dict(m) for m in import_meters],
        "export_meters": [_meter_to_dict(m) for m in export_meters],
        "property_count": len(account.get("properties") or []),
    }
