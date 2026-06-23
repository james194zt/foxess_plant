"""Parse Octopus rate timelines from Home Assistant entity attributes (entity mode)."""

from __future__ import annotations

from typing import Any

RATE_LIST_KEYS = ("rates", "all_rates", "applicable_rates", "rate_list", "unit_rates")
ROW_VALUE_KEYS = ("value_inc_vat", "rate", "value", "price")
ROW_START_KEYS = ("valid_from", "start", "from")
ROW_END_KEYS = ("valid_to", "end", "to")


def value_to_pence(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if abs(value) < 2.0:
        return round(value * 100.0, 4)
    return round(value, 4)


def normalize_entity_rate_row(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    start = None
    end = None
    for key in ROW_START_KEYS:
        if row.get(key) is not None:
            start = row.get(key)
            break
    for key in ROW_END_KEYS:
        if row.get(key) is not None:
            end = row.get(key)
            break
    price = None
    for key in ROW_VALUE_KEYS:
        if row.get(key) is not None:
            price = value_to_pence(row.get(key))
            break
    if start is None or price is None:
        return None
    out: dict[str, Any] = {"valid_from": start, "value_inc_vat": price}
    if end is not None:
        out["valid_to"] = end
    tariff_code = row.get("tariff_code") or row.get("tariff")
    if tariff_code:
        out["tariff_code"] = str(tariff_code)
    return out


def collect_rate_rows_from_attributes(attrs: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(attrs, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key in RATE_LIST_KEYS:
        raw = attrs.get(key)
        if not isinstance(raw, list):
            continue
        for item in raw:
            normalized = normalize_entity_rate_row(item)
            if normalized:
                rows.append(normalized)
        if rows:
            break
    if not rows:
        single = attrs.get("rate")
        if isinstance(single, dict):
            normalized = normalize_entity_rate_row(single)
            if normalized:
                rows.append(normalized)
    if not rows and any(attrs.get(k) is not None for k in ROW_START_KEYS):
        normalized = normalize_entity_rate_row(attrs)
        if normalized:
            rows.append(normalized)
    return rows


def merge_rate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedupe by valid_from, keeping first occurrence."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.get("valid_from"))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    out.sort(key=lambda item: str(item.get("valid_from")))
    return out


def tariff_code_from_attributes(attrs: dict[str, Any]) -> str | None:
    for key in ("tariff_code", "tariff", "product_code"):
        raw = attrs.get(key)
        if raw:
            return str(raw)
    rows = collect_rate_rows_from_attributes(attrs)
    for row in rows:
        code = row.get("tariff_code")
        if code:
            return str(code)
    return None
