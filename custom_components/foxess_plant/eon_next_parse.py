"""E.ON Next (Kraken) response parsing — stdlib only so it can be unit tested without HA.

E.ON Next runs on Kraken like Octopus, but its GraphQL schema differs:
``electricityMeterPoints`` (not ``electricitySupplyPoints``), a ``direction`` field that
marks IMPORT/EXPORT, and import/export can sit on separate account numbers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

EON_NEXT_PROVIDER = "eon_next"

TARIFF_TYPE_GO = "go"
TARIFF_TYPE_ECONOMY7 = "economy7"
TARIFF_TYPE_FLAT = "flat"

# Kraken sends null valid_from on flat-rate rows. rate_at() skips rows without a start,
# so open-ended rows get a start far enough back to cover any sampled hour.
OPEN_START_ISO = "2000-01-01T00:00:00Z"

_EXPORT_MARKERS = ("EXPORT", "OUTGOING", "-SEG-", "SEG-")


def parse_iso(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def classify_eon_tariff_code(tariff_code: str | None) -> str:
    """Map an E.ON Next tariff code onto the plant's tariff types.

    E.ON has no half-hourly Agile-style product. Time-of-use tariffs (Next Drive,
    ``E-TOU-*``) behave like Octopus Go: a fixed cheap window every night.
    """
    code = str(tariff_code or "").upper()
    if code.startswith("E-TOU") or "-TOU-" in code or "DRIVE" in code:
        return TARIFF_TYPE_GO
    if code.startswith("E-2R"):
        return TARIFF_TYPE_ECONOMY7
    return TARIFF_TYPE_FLAT


def agreement_active(agreement: dict[str, Any], now: datetime) -> bool:
    start = parse_iso(agreement.get("validFrom"))
    end = parse_iso(agreement.get("validTo"))
    if start is not None and now < start:
        return False
    if end is not None and end <= now:
        return False
    return True


def meter_point_is_export(meter_point: dict[str, Any], tariff_code: str | None) -> bool:
    direction = meter_point.get("direction")
    if isinstance(direction, str) and direction.strip():
        return direction.strip().upper() == "EXPORT"
    code = str(tariff_code or "").upper()
    return any(marker in code for marker in _EXPORT_MARKERS)


def meters_from_accounts(
    accounts: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Flatten ``account { properties { electricityMeterPoints } }`` into import/export meters.

    Each meter keeps its account number: rates for an export MPAN on a separate E.ON
    account must be queried against that account.
    """
    now = now or datetime.now(timezone.utc)
    imports: list[dict[str, Any]] = []
    exports: list[dict[str, Any]] = []
    seen: set[str] = set()
    for account in accounts:
        if not isinstance(account, dict):
            continue
        account_number = str(account.get("number") or "").strip().upper()
        for prop in account.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            for point in prop.get("electricityMeterPoints") or []:
                if not isinstance(point, dict):
                    continue
                mpan = str(point.get("mpan") or "").strip()
                if not mpan or mpan in seen:
                    continue
                seen.add(mpan)
                active = next(
                    (
                        a
                        for a in point.get("agreements") or []
                        if isinstance(a, dict) and agreement_active(a, now)
                    ),
                    None,
                )
                tariff = (active or {}).get("tariff") or {}
                tariff_code = str(tariff.get("tariffCode") or "").strip() or None
                product_code = str(tariff.get("productCode") or "").strip() or None
                is_export = meter_point_is_export(point, tariff_code)
                display = str(tariff.get("displayName") or "").strip()
                meter = {
                    "account_number": account_number,
                    "mpan": mpan,
                    "is_export": is_export,
                    "tariff_code": tariff_code,
                    "product_code": product_code,
                    "display_name": f"{mpan} — {display}" if display else mpan,
                }
                (exports if is_export else imports).append(meter)
    return imports, exports


def pick_meter(
    meters: list[dict[str, Any]],
    mpan: str | None,
    *,
    role: str,
    preferred_account: str | None = None,
    allow_first: bool = False,
) -> dict[str, Any] | None:
    """Pick the configured MPAN, else the only meter, else (if allowed) the best guess.

    Raises ValueError with a UI-ready message when the choice is ambiguous.
    """
    if mpan:
        target = str(mpan).strip()
        for meter in meters:
            if meter["mpan"] == target:
                return meter
        raise ValueError(f"Meter MPAN {target} was not found on this E.ON Next login")
    if not meters:
        return None
    candidates = meters
    if preferred_account:
        same = [m for m in meters if m["account_number"] == preferred_account.strip().upper()]
        candidates = same or meters
    if len(candidates) == 1:
        return candidates[0]
    if allow_first:
        with_tariff = [m for m in candidates if m["tariff_code"]]
        return (with_tariff or candidates)[0]
    raise ValueError(
        f"Multiple {role} electricity meters found — select an {role} MPAN in E.ON Next settings"
    )


def normalize_rest_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give open-ended REST rows a start so rate_at() and the schedule builder see them."""
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("value_inc_vat") is None:
            continue
        fixed = dict(row)
        if not fixed.get("valid_from"):
            fixed["valid_from"] = OPEN_START_ISO
        out.append(fixed)
    return out


def graphql_nodes_to_rows(connection: Any) -> list[dict[str, Any]]:
    """Convert an ``applicableRates``/``applicableStandingCharges`` connection to REST-shaped rows.

    ``value`` is inc-VAT pence (per kWh or per day).
    """
    if isinstance(connection, list):
        nodes = connection
    elif isinstance(connection, dict):
        nodes = [e.get("node") for e in connection.get("edges") or [] if isinstance(e, dict)]
    else:
        nodes = []
    rows: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict) or node.get("value") is None:
            continue
        try:
            value = float(node["value"])
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "value_inc_vat": value,
                "value_exc_vat": round(value / 1.05, 4),
                "valid_from": node.get("validFrom"),
                "valid_to": node.get("validTo"),
            }
        )
    return normalize_rest_rows(rows)


def graphql_error_code(errors: Any) -> str | None:
    if not isinstance(errors, list) or not errors:
        return None
    first = errors[0] if isinstance(errors[0], dict) else {}
    ext = first.get("extensions")
    code = ext.get("errorCode") if isinstance(ext, dict) else None
    return str(code) if code else None


def graphql_error_message(errors: Any) -> str:
    if not isinstance(errors, list) or not errors:
        return "E.ON Next GraphQL error"
    first = errors[0] if isinstance(errors[0], dict) else {}
    message = str(first.get("message") or "E.ON Next GraphQL error")
    code = graphql_error_code(errors)
    return f"{message} ({code})" if code else message
