"""Tariff currency helpers — minor-unit storage with ISO 4217 metadata."""

from __future__ import annotations

from .const import TARIFF_CURRENCIES

_MAJOR_UNIT_CODES = frozenset(
    {
        "gbp",
        "eur",
        "usd",
        "aud",
        "cad",
        "nzd",
        "chf",
        "sek",
        "nok",
        "dkk",
        "pln",
        "czk",
        "huf",
        "ron",
        "bgn",
        "try",
        "ils",
        "zar",
        "brl",
        "mxn",
        "sgd",
        "hkd",
        "inr",
        "cny",
        "jpy",
        "krw",
    }
)


def normalize_tariff_currency(code: str | None) -> str:
    raw = str(code or "GBP").upper().strip()[:3]
    return raw if raw in TARIFF_CURRENCIES else "GBP"


def tariff_currency_decimals(code: str | None) -> int:
    meta = TARIFF_CURRENCIES.get(normalize_tariff_currency(code), {})
    decimals = meta.get("decimals", 2)
    return int(decimals) if isinstance(decimals, int) else 2


def tariff_minor_factor(code: str | None) -> int:
    decimals = tariff_currency_decimals(code)
    return 10**decimals if decimals > 0 else 1


def minor_to_major(minor: float, code: str | None) -> float:
    factor = tariff_minor_factor(code)
    return round(float(minor or 0) / factor, max(tariff_currency_decimals(code), 4))


def major_to_minor(major: float, code: str | None) -> float:
    factor = tariff_minor_factor(code)
    return round(float(major or 0) * factor, 4)


def entity_value_to_minor_per_kwh(value: float, unit: str | None, currency: str | None) -> float | None:
    """Convert a sensor reading to tariff minor units per kWh."""
    if value < 0:
        return None
    factor = tariff_minor_factor(currency)
    u = _normalize_unit(unit)
    if not u:
        if 0 < value <= 5:
            return round(value * factor, 4)
        if value > 0:
            return round(value, 4)
        return None
    if "p/kwh" in u or "pence/kwh" in u or u in ("p", "pence", "c", "cent", "cents"):
        return round(value, 4)
    if "/kwh" in u or u.endswith("kwh"):
        if u.startswith("p") or u.startswith("pence") or u.startswith("c") or u.startswith("cent"):
            return round(value, 4)
        if any(u.startswith(code) or f"{code}/" in u for code in _MAJOR_UNIT_CODES):
            return round(value * factor, 4)
        return round(value * factor, 4)
    if u in _MAJOR_UNIT_CODES and 0 < value <= 5:
        return round(value * factor, 4)
    return None


def entity_value_to_minor_per_day(value: float, unit: str | None, currency: str | None) -> float | None:
    """Convert a sensor reading to tariff minor units per day."""
    if value < 0:
        return None
    factor = tariff_minor_factor(currency)
    u = _normalize_unit(unit)
    if not u:
        if 0 < value <= 5:
            return round(value * factor, 4)
        if value > 0:
            return round(value, 4)
        return None
    if "p/day" in u or "pence/day" in u or "c/day" in u or "cent/day" in u:
        return round(value, 4)
    if "/day" in u or "daily" in u or "perday" in u:
        if u.startswith("p") or u.startswith("pence") or u.startswith("c") or u.startswith("cent"):
            return round(value, 4)
        return round(value * factor, 4)
    if u in _MAJOR_UNIT_CODES and 0 < value <= 5:
        return round(value * factor, 4)
    return None


def _normalize_unit(unit: str | None) -> str:
    if not unit:
        return ""
    u = str(unit).lower().replace(" ", "")
    return u.replace("gb£", "gbp").replace("£", "gbp").replace("€", "eur").replace("$", "usd")
