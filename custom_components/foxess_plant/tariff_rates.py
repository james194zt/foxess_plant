"""Resolve tariff rates from manual values or Home Assistant sensor entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant, State

from .tariff_currency import (
    entity_value_to_minor_per_day,
    entity_value_to_minor_per_kwh,
    normalize_tariff_currency,
)
from .tariff_schedule import TARIFF_SOURCE_PLUGIN, TARIFF_SOURCE_SCHEDULE

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


def _resolve_plugin_sensor_minor(
    hass: HomeAssistant,
    entity_id: str | None,
    *,
    per_day: bool,
    currency: str,
) -> tuple[float | None, dict[str, Any] | None]:
    """Read plugin-owned tariff sensors (stored in major units on the entity)."""
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
            "source": "plugin",
        }
    value = _parse_float(state.state)
    unit = state.attributes.get("unit_of_measurement")
    resolved = None
    if value is not None:
        from .tariff_currency import major_to_minor

        resolved = (
            major_to_minor(value, currency)
            if per_day
            else major_to_minor(value, currency)
        )
        if not per_day and resolved is not None:
            resolved = round(resolved, 4)
    band_index = state.attributes.get("band_index")
    meta = {
        "entity_id": entity_id,
        "state": state.state,
        "unit": str(unit) if unit else None,
        "available": True,
        "resolved_p": resolved,
        "friendly_name": state.attributes.get("friendly_name"),
        "source": "plugin",
    }
    if band_index is not None:
        meta["band_index"] = band_index
    return resolved, meta


def scheduled_rates_at(tariff: Any, when: datetime | None = None) -> dict[str, Any]:
    """Current schedule band and import/export minor rates for a datetime."""
    schedule = tariff.schedule_config() if hasattr(tariff, "schedule_config") else None
    if schedule is None:
        from .tariff_schedule import TariffScheduleConfig

        schedule = TariffScheduleConfig.from_dict(getattr(tariff, "schedule", None))
    return schedule.rates_at(when)


def resolve_tariff_rates(
    hass: HomeAssistant,
    tariff: Any,
    *,
    entry_id: str | None = None,
    when: datetime | None = None,
) -> dict[str, Any]:
    """Resolve effective minor-unit rates and entity metadata for panel / analysis."""
    from .tariff_schedule import tariff_plugin_entity_id

    currency = normalize_tariff_currency(getattr(tariff, "currency", None))
    import_p = float(getattr(tariff, "import_p_per_kwh", 0) or 0)
    export_p = float(getattr(tariff, "export_p_per_kwh", 0) or 0)
    standing_p = max(0.0, float(getattr(tariff, "standing_charge_p_per_day", 0) or 0))

    entities: dict[str, Any] = {}
    schedule_meta: dict[str, Any] = {}
    entry_id = entry_id or getattr(tariff, "entry_id", None)

    scheduled = scheduled_rates_at(tariff, when)
    schedule_meta = {
        "hour": scheduled.get("hour"),
        "band_index": scheduled.get("band_index"),
    }

    import_source = getattr(tariff, "import_source", TARIFF_SOURCE_MANUAL)
    if import_source == TARIFF_SOURCE_SCHEDULE:
        import_p = float(scheduled.get("import_p_per_kwh", import_p) or 0)
        plugin_id = None
        if entry_id:
            plugin_id = tariff_plugin_entity_id(hass, entry_id, "import")
        if plugin_id:
            resolved, meta = _resolve_plugin_sensor_minor(
                hass, plugin_id, per_day=False, currency=currency
            )
            entities["import"] = meta
            if resolved is not None:
                import_p = resolved
        entities.setdefault(
            "import",
            {
                "entity_id": plugin_id,
                "available": plugin_id is not None,
                "resolved_p": import_p,
                "source": "schedule",
                **schedule_meta,
            },
        )
    elif import_source == TARIFF_SOURCE_ENTITY:
        resolved, meta = _resolve_entity_minor(
            hass, getattr(tariff, "import_entity", None), per_day=False, currency=currency
        )
        entities["import"] = meta
        if resolved is not None:
            import_p = resolved

    export_source = getattr(tariff, "export_source", TARIFF_SOURCE_MANUAL)
    if export_source == TARIFF_SOURCE_SCHEDULE:
        export_p = float(scheduled.get("export_p_per_kwh", export_p) or 0)
        plugin_id = None
        if entry_id:
            plugin_id = tariff_plugin_entity_id(hass, entry_id, "export")
        if plugin_id:
            resolved, meta = _resolve_plugin_sensor_minor(
                hass, plugin_id, per_day=False, currency=currency
            )
            entities["export"] = meta
            if resolved is not None:
                export_p = resolved
        entities.setdefault(
            "export",
            {
                "entity_id": plugin_id,
                "available": plugin_id is not None,
                "resolved_p": export_p,
                "source": "schedule",
                **schedule_meta,
            },
        )
    elif export_source == TARIFF_SOURCE_ENTITY:
        resolved, meta = _resolve_entity_minor(
            hass, getattr(tariff, "export_entity", None), per_day=False, currency=currency
        )
        entities["export"] = meta
        if resolved is not None:
            export_p = resolved

    standing_source = getattr(tariff, "standing_source", TARIFF_SOURCE_MANUAL)
    if standing_source == TARIFF_SOURCE_PLUGIN:
        standing_p = max(0.0, float(getattr(tariff, "standing_charge_p_per_day", 0) or 0))
        plugin_id = None
        if entry_id:
            plugin_id = tariff_plugin_entity_id(hass, entry_id, "standing")
        if plugin_id:
            resolved, meta = _resolve_plugin_sensor_minor(
                hass, plugin_id, per_day=True, currency=currency
            )
            entities["standing"] = meta
            if resolved is not None:
                standing_p = resolved
        entities.setdefault(
            "standing",
            {
                "entity_id": plugin_id,
                "available": plugin_id is not None,
                "resolved_p": standing_p,
                "source": "plugin",
            },
        )
    elif standing_source == TARIFF_SOURCE_ENTITY:
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
        "schedule": schedule_meta,
    }
