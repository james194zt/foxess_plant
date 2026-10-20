"""Glow smart-meter parsing and grid-only analytics overlay."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

GLOW_ERROR_POWER_KW = -8388.608
# The IHD publishes about every 10 s; older than this and the live power is no longer trusted.
GLOW_POWER_MAX_AGE_S = 120


def normalize_glow_device_id(device_id: str | None) -> str:
    raw = str(device_id or "+").strip().upper()
    if raw in ("", "+"):
        return "+"
    return raw.replace(":", "").replace(" ", "")


def parse_glow_electricity_payload(payload: dict[str, Any], *, source: str = "glow_mqtt") -> dict[str, Any] | None:
    """Parse Glow IHD electricity MQTT/API JSON into a normalized live snapshot."""
    block = payload.get("electricitymeter")
    if not isinstance(block, dict):
        return None
    energy = block.get("energy") if isinstance(block.get("energy"), dict) else {}
    imp = energy.get("import") if isinstance(energy.get("import"), dict) else {}
    exp = energy.get("export") if isinstance(energy.get("export"), dict) else {}
    power = block.get("power") if isinstance(block.get("power"), dict) else {}

    import_kw = _float(power.get("value"))
    if import_kw == GLOW_ERROR_POWER_KW:
        import_kw = None

    price = imp.get("price") if isinstance(imp.get("price"), dict) else {}
    ts = _parse_ts(block.get("timestamp") or payload.get("timestamp"))

    return {
        "source": source,
        "timestamp": ts,
        "import_kw": import_kw,
        "import_kwh_cumulative": _float(imp.get("cumulative")),
        "import_kwh_today": _float(imp.get("day")),
        "import_kwh_week": _float(imp.get("week")),
        "import_kwh_month": _float(imp.get("month")),
        "export_kwh_cumulative": _float(exp.get("cumulative")),
        "mpan": imp.get("mpan"),
        "supplier": imp.get("supplier"),
        "import_unit_rate_gbp": _float(price.get("unitrate")),
        "import_standing_charge_gbp": _float(price.get("standingcharge")),
    }


def apply_glow_grid_overlay(
    analytics: dict[str, Any],
    glow_live: dict[str, Any] | None,
    *,
    enabled: bool,
) -> dict[str, Any]:
    """Replace grid import/export fields with Glow smart-meter data; PV stays from plant."""
    if not enabled or not glow_live:
        return analytics

    out = dict(analytics) if analytics else {}
    if glow_live.get("import_kwh_today") is not None:
        out["load_from_grid_kwh_today"] = round(float(glow_live["import_kwh_today"]), 2)
    if glow_live.get("import_kw") is not None:
        out["grid_import_kw_live"] = round(float(glow_live["import_kw"]), 3)
    if glow_live.get("export_kwh_today") is not None:
        out["pv_to_grid_kwh_today"] = round(float(glow_live["export_kwh_today"]), 2)
    out["grid_data_source"] = glow_live.get("source") or "glow"

    if analytics and glow_live.get("import_kwh_today") is not None:
        from .analytics import load_from_pv_battery_kwh

        load_cons = float(analytics.get("load_consumption_kwh_today") or 0)
        from_grid = float(out.get("load_from_grid_kwh_today") or 0)
        from_pv_battery = load_from_pv_battery_kwh(
            load=load_cons,
            from_grid=from_grid,
            pv=float(analytics.get("pv_production_kwh_today") or 0),
            to_grid=float(out.get("pv_to_grid_kwh_today") or 0),
            charge=float(analytics.get("battery_charge_kwh_today") or 0),
        )
        out["load_from_pv_battery_kwh_today"] = round(from_pv_battery, 2)
        if load_cons > 0:
            out["self_sufficiency_percent_today"] = round(
                min(100.0, max(0.0, (from_pv_battery / load_cons) * 100)),
                1,
            )
    return out


def glow_net_power_kw(
    glow_live: dict[str, Any] | None,
    *,
    now: datetime | None = None,
    max_age_s: float = GLOW_POWER_MAX_AGE_S,
) -> float | None:
    """Fresh Glow meter power in kW (import positive, export negative), else None."""
    live = glow_live if isinstance(glow_live, dict) else {}
    power = _float(live.get("import_kw"))
    raw_ts = live.get("timestamp")
    if power is None or not raw_ts:
        return None
    ts = dt_util.parse_datetime(str(raw_ts))
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt_util.UTC)
    age = ((now or dt_util.utcnow()) - ts).total_seconds()
    if age > max_age_s:
        return None
    return power


def pick_grid_power_kw(
    *,
    ct_import_kw: float | None,
    ct_export_kw: float | None,
    glow_net_kw: float | None,
    import_from_glow: bool,
    export_from_glow: bool,
) -> tuple[float | None, float | None, dict[str, str]]:
    """Grid import/export kW, each from Glow or the inverter CT as configured.

    Glow wins a direction only when its option is on and the reading is fresh; otherwise that
    direction falls back to the inverter CT, so a dropped meter feed never blanks the grid.
    """
    import_kw, export_kw = ct_import_kw, ct_export_kw
    sources = {"import": "inverter", "export": "inverter"}
    if glow_net_kw is not None:
        if import_from_glow:
            import_kw = max(0.0, glow_net_kw)
            sources["import"] = "glow"
        if export_from_glow:
            export_kw = max(0.0, -glow_net_kw)
            sources["export"] = "glow"
    return import_kw, export_kw, sources


def glow_status_dict(config: Any, live: dict[str, Any] | None) -> dict[str, Any]:
    """Panel-friendly Glow status (secrets redacted)."""
    live = live if isinstance(live, dict) else {}
    cfg = config.to_dict(include_secrets=False) if hasattr(config, "to_dict") else {}
    mqtt_age_s = None
    ts = live.get("timestamp") or cfg.get("last_mqtt_at")
    if ts:
        parsed = dt_util.parse_datetime(str(ts))
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt_util.UTC)
            mqtt_age_s = int((dt_util.utcnow() - parsed).total_seconds())

    return {
        **cfg,
        "live": {
            "import_kw": live.get("import_kw"),
            "import_kwh_today": live.get("import_kwh_today"),
            "import_kwh_cumulative": live.get("import_kwh_cumulative"),
            "export_kwh_today": live.get("export_kwh_today"),
            "export_kwh_cumulative": live.get("export_kwh_cumulative"),
            "timestamp": live.get("timestamp"),
            "source": live.get("source"),
            "mpan": live.get("mpan"),
        },
        "mqtt_connected": bool(cfg.get("mqtt_connected")),
        "mqtt_age_seconds": mqtt_age_s,
        "grid_active": bool(cfg.get("enabled")) and bool(live.get("import_kwh_today") is not None or live.get("import_kw") is not None),
    }


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_ts(raw: Any) -> str | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        dt = dt_util.parse_datetime(str(raw))
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_util.UTC)
    return dt_util.as_utc(dt).isoformat()
