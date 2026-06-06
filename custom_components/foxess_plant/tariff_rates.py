"""Resolve tariff rates from manual values or Home Assistant sensor entities."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, State

from .tariff_currency import (
    entity_value_to_minor_per_day,
    entity_value_to_minor_per_kwh,
    normalize_tariff_currency,
)

TARIFF_SOURCE_MANUAL = "manual"
TARIFF_SOURCE_ENTITY = "entity"

RATE_KIND_IMPORT = "import"
RATE_KIND_EXPORT = "export"
RATE_KIND_STANDING = "standing"

_IMPORT_HINTS = (
    "import",
    "consumption",
    "buy",
    "unit_rate",
    "electricity_rate",
    "electricity",
    "glow",
    "octopus",
    "agile",
    "tariff",
    "rate",
)
_EXPORT_HINTS = (
    "export",
    "feed_in",
    "feed-in",
    "feedin",
    "seg",
    "sell",
    "export_rate",
    "tariff",
    "rate",
)
_STANDING_HINTS = (
    "standing",
    "daily_charge",
    "daily_standing",
    "standing_charge",
    "fixed",
    "daily",
)


def _parse_float(raw: str | None) -> float | None:
    if raw in (None, "", "unknown", "unavailable"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _normalize_unit(unit: str | None) -> str:
    from .tariff_currency import _normalize_unit as normalize

    return normalize(unit)


# Backwards-compatible aliases (stored values are currency minor units).
entity_value_to_pence_per_kwh = entity_value_to_minor_per_kwh
entity_value_to_pence_per_day = entity_value_to_minor_per_day


def _entity_blob(state: State) -> str:
    name = state.attributes.get("friendly_name") or ""
    return f"{state.entity_id} {name}".lower()


def tariff_rate_kinds(state: State) -> list[str]:
    """Which tariff rate slots this sensor plausibly feeds."""
    return _tariff_rate_kinds(state)


def _tariff_rate_kinds(state: State) -> list[str]:
    """Which tariff rate slots this sensor plausibly feeds."""
    if not state.entity_id.startswith("sensor."):
        return []
    value = _parse_float(state.state)
    if value is None:
        return []
    unit = _normalize_unit(state.attributes.get("unit_of_measurement"))
    blob = _entity_blob(state)
    kinds: list[str] = []

    per_kwh = entity_value_to_minor_per_kwh(value, unit, "GBP") is not None
    per_day = entity_value_to_minor_per_day(value, unit, "GBP") is not None

    if per_kwh:
        if any(h in blob for h in _IMPORT_HINTS) and "export" not in blob and "feed" not in blob:
            kinds.append(RATE_KIND_IMPORT)
        if any(h in blob for h in _EXPORT_HINTS) and "import" not in blob and "consumption" not in blob:
            kinds.append(RATE_KIND_EXPORT)
        if not kinds and any(h in blob for h in ("rate", "tariff", "price", "cost", "unit")):
            kinds.extend([RATE_KIND_IMPORT, RATE_KIND_EXPORT])
        if not kinds and ("/kwh" in unit or unit.endswith("kwh") or unit in ("gbp", "p", "pence")):
            kinds.extend([RATE_KIND_IMPORT, RATE_KIND_EXPORT])

    if per_day:
        if any(h in blob for h in _STANDING_HINTS):
            kinds.append(RATE_KIND_STANDING)
        elif "/day" in unit or "daily" in unit:
            kinds.append(RATE_KIND_STANDING)

    return sorted(set(kinds))


def _resolve_entity_minor(
    hass: HomeAssistant,
    entity_id: str | None,
    *,
    per_day: bool,
    currency: str,
) -> tuple[float | None, dict[str, Any] | None]:
    if not entity_id:
        return None, None
    state = hass.states.get(entity_id)
    if state is None:
        return None, {
            "entity_id": entity_id,
            "state": None,
            "unit": None,
            "available": False,
            "resolved_p": None,
        }
    value = _parse_float(state.state)
    unit = state.attributes.get("unit_of_measurement")
    resolved = None
    if value is not None:
        resolved = (
            entity_value_to_minor_per_day(value, unit, currency)
            if per_day
            else entity_value_to_minor_per_kwh(value, unit, currency)
        )
    return resolved, {
        "entity_id": entity_id,
        "state": state.state,
        "unit": str(unit) if unit else None,
        "available": True,
        "resolved_p": resolved,
        "friendly_name": state.attributes.get("friendly_name"),
    }


def resolve_tariff_rates(hass: HomeAssistant, tariff: Any) -> dict[str, Any]:
    """Resolve effective minor-unit rates and entity metadata for panel / analysis."""
    currency = normalize_tariff_currency(getattr(tariff, "currency", None))
    import_p = max(0.0, float(getattr(tariff, "import_p_per_kwh", 0) or 0))
    export_p = max(0.0, float(getattr(tariff, "export_p_per_kwh", 0) or 0))
    standing_p = max(0.0, float(getattr(tariff, "standing_charge_p_per_day", 0) or 0))

    entities: dict[str, Any] = {}

    if getattr(tariff, "import_source", TARIFF_SOURCE_MANUAL) == TARIFF_SOURCE_ENTITY:
        resolved, meta = _resolve_entity_minor(
            hass, getattr(tariff, "import_entity", None), per_day=False, currency=currency
        )
        entities["import"] = meta
        if resolved is not None:
            import_p = resolved

    if getattr(tariff, "export_source", TARIFF_SOURCE_MANUAL) == TARIFF_SOURCE_ENTITY:
        resolved, meta = _resolve_entity_minor(
            hass, getattr(tariff, "export_entity", None), per_day=False, currency=currency
        )
        entities["export"] = meta
        if resolved is not None:
            export_p = resolved

    if getattr(tariff, "standing_source", TARIFF_SOURCE_MANUAL) == TARIFF_SOURCE_ENTITY:
        resolved, meta = _resolve_entity_minor(
            hass, getattr(tariff, "standing_entity", None), per_day=True, currency=currency
        )
        entities["standing"] = meta
        if resolved is not None:
            standing_p = resolved

    return {
        "currency": currency,
        "effective": {
            "import_p_per_kwh": round(import_p, 4),
            "export_p_per_kwh": round(export_p, 4),
            "standing_charge_p_per_day": round(standing_p, 4),
        },
        "entities": entities,
    }
