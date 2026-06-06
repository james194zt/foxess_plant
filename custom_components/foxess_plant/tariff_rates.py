"""Resolve tariff rates from manual values or Home Assistant sensor entities."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, State

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


def _normalize_unit(unit: str | None) -> str:
    if not unit:
        return ""
    u = str(unit).lower().replace(" ", "")
    return u.replace("gb£", "gbp").replace("£", "gbp")


def _parse_float(raw: str | None) -> float | None:
    if raw in (None, "", "unknown", "unavailable"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def entity_value_to_pence_per_kwh(value: float, unit: str | None) -> float | None:
    """Convert a sensor reading to pence per kWh."""
    if value < 0:
        return None
    u = _normalize_unit(unit)
    if not u:
        if 0 < value <= 5:
            return round(value * 100, 4)
        if value > 0:
            return round(value, 4)
        return None
    if "p/kwh" in u or "pence/kwh" in u or u in ("p", "pence"):
        return round(value, 4)
    if "/kwh" in u or u.endswith("kwh"):
        if u.startswith("p") or (u.startswith("pence") and "gbp" not in u):
            return round(value, 4)
        return round(value * 100, 4)
    if u in ("gbp", "eur", "usd") and 0 < value <= 5:
        return round(value * 100, 4)
    return None


def entity_value_to_pence_per_day(value: float, unit: str | None) -> float | None:
    """Convert a sensor reading to pence per day."""
    if value < 0:
        return None
    u = _normalize_unit(unit)
    if not u:
        if 0 < value <= 5:
            return round(value * 100, 4)
        if value > 0:
            return round(value, 4)
        return None
    if "p/day" in u or "pence/day" in u:
        return round(value, 4)
    if "/day" in u or "daily" in u or "perday" in u:
        if u.startswith("p") or (u.startswith("pence") and "gbp" not in u):
            return round(value, 4)
        return round(value * 100, 4)
    if u in ("gbp", "eur", "usd") and 0 < value <= 5:
        return round(value * 100, 4)
    return None


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

    per_kwh = entity_value_to_pence_per_kwh(value, unit) is not None
    per_day = entity_value_to_pence_per_day(value, unit) is not None

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


def _resolve_entity_pence(
    hass: HomeAssistant,
    entity_id: str | None,
    *,
    per_day: bool,
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
            entity_value_to_pence_per_day(value, unit)
            if per_day
            else entity_value_to_pence_per_kwh(value, unit)
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
    """Resolve effective pence rates and entity metadata for panel / analysis."""
    import_p = max(0.0, float(getattr(tariff, "import_p_per_kwh", 0) or 0))
    export_p = max(0.0, float(getattr(tariff, "export_p_per_kwh", 0) or 0))
    standing_p = max(0.0, float(getattr(tariff, "standing_charge_p_per_day", 0) or 0))

    entities: dict[str, Any] = {}

    if getattr(tariff, "import_source", TARIFF_SOURCE_MANUAL) == TARIFF_SOURCE_ENTITY:
        resolved, meta = _resolve_entity_pence(hass, getattr(tariff, "import_entity", None), per_day=False)
        entities["import"] = meta
        if resolved is not None:
            import_p = resolved

    if getattr(tariff, "export_source", TARIFF_SOURCE_MANUAL) == TARIFF_SOURCE_ENTITY:
        resolved, meta = _resolve_entity_pence(hass, getattr(tariff, "export_entity", None), per_day=False)
        entities["export"] = meta
        if resolved is not None:
            export_p = resolved

    if getattr(tariff, "standing_source", TARIFF_SOURCE_MANUAL) == TARIFF_SOURCE_ENTITY:
        resolved, meta = _resolve_entity_pence(hass, getattr(tariff, "standing_entity", None), per_day=True)
        entities["standing"] = meta
        if resolved is not None:
            standing_p = resolved

    return {
        "effective": {
            "import_p_per_kwh": round(import_p, 4),
            "export_p_per_kwh": round(export_p, 4),
            "standing_charge_p_per_day": round(standing_p, 4),
        },
        "entities": entities,
    }
