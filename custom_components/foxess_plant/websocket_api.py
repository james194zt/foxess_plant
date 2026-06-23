"""WebSocket API for the Fox Plant panel."""

from __future__ import annotations

import logging
from functools import partial
from datetime import datetime as dt, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.recorder import get_instance, history
from homeassistant.components.recorder.util import session_scope
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STORM_ALERT_PROVIDER_GOOGLE, TARIFF_CURRENCIES
from .panel_config import list_forecast_entity_candidates, list_tariff_entity_candidates, list_trigger_candidates

_LOGGER = logging.getLogger(__name__)

WS_TYPE_PLANT_STATE = "foxess_plant/plant_state"
WS_TYPE_PLANT_LIST = "foxess_plant/plant_list"
WS_TYPE_TRIGGER_CANDIDATES = "foxess_plant/trigger_candidates"
WS_TYPE_UPDATE_STORM_PREP = "foxess_plant/update_storm_prep"
WS_TYPE_SET_SOC_LIMITS = "foxess_plant/set_soc_limits"
WS_TYPE_FORECAST_ENTITY_CANDIDATES = "foxess_plant/forecast_entity_candidates"
WS_TYPE_UPDATE_PANEL_DISPLAY = "foxess_plant/update_panel_display"
WS_TYPE_UPDATE_PV_CONFIG = "foxess_plant/update_pv_config"
WS_TYPE_UPDATE_TARIFF = "foxess_plant/update_tariff"
WS_TYPE_UPDATE_OCTOPUS = "foxess_plant/update_octopus"
WS_TYPE_TEST_OCTOPUS = "foxess_plant/test_octopus"
WS_TYPE_FETCH_OCTOPUS = "foxess_plant/fetch_octopus"
WS_TYPE_FETCH_OCTOPUS_ANALYSIS = "foxess_plant/fetch_octopus_analysis"
WS_TYPE_APPLY_OCTOPUS_SCHEDULE = "foxess_plant/apply_octopus_schedule"
WS_TYPE_UPDATE_SMART_CHARGE = "foxess_plant/update_smart_charge"
WS_TYPE_TARIFF_ENTITY_CANDIDATES = "foxess_plant/tariff_entity_candidates"
WS_TYPE_UPDATE_SOLCAST = "foxess_plant/update_solcast"
WS_TYPE_TEST_SOLCAST = "foxess_plant/test_solcast"
WS_TYPE_UPDATE_GLOW = "foxess_plant/update_glow"
WS_TYPE_TEST_GLOW = "foxess_plant/test_glow"
WS_TYPE_FETCH_HISTORY = "foxess_plant/fetch_history"
WS_TYPE_FETCH_STATISTICS = "foxess_plant/fetch_statistics"
WS_TYPE_SOLCAST_FORECAST_INTRADAY = "foxess_plant/solcast_forecast_intraday"
WS_TYPE_SOLCAST_FORECAST_ACCURACY = "foxess_plant/solcast_forecast_accuracy"
WS_TYPE_SOLCAST_STATISTICS_FORECAST = "foxess_plant/solcast_statistics_forecast"

PERIOD_SCHEMA = vol.Schema(
    {
        vol.Required("enable_force_charge"): cv.boolean,
        vol.Required("enable_charge_from_grid"): cv.boolean,
        vol.Optional("start", default="00:00"): cv.string,
        vol.Optional("end", default="00:00"): cv.string,
    }
)

PV_STRING_SCHEMA = vol.Schema(
    {
        vol.Required("enabled"): cv.boolean,
        vol.Required("panel_count"): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
        vol.Required("watts_per_panel"): vol.All(vol.Coerce(int), vol.Range(min=100, max=1000)),
        vol.Required("efficiency_factor"): vol.All(vol.Coerce(float), vol.Range(min=1, max=100)),
        vol.Required("tilt"): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
        vol.Required("azimuth"): vol.All(vol.Coerce(int), vol.Range(min=0, max=359)),
        vol.Optional("installation_cost_minor", default=0): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=99_999_999)
        ),
    }
)

PV_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional("annual_degradation_pct", default=2.0): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=10)
        ),
        vol.Required("pv1"): PV_STRING_SCHEMA,
        vol.Required("pv2"): PV_STRING_SCHEMA,
    }
)

SOLCAST_SCHEMA = vol.Schema(
    {
        vol.Required("enabled"): cv.boolean,
        vol.Optional("api_key"): vol.Any(str, None),
        vol.Required("api_limit"): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Required("auto_update"): vol.In(["daylight", "all_day"]),
        vol.Optional("latitude"): vol.Any(vol.Coerce(float), None),
        vol.Optional("longitude"): vol.Any(vol.Coerce(float), None),
        vol.Optional("installation_date"): vol.Any(str, None),
        vol.Optional("period", default="PT30M"): str,
        vol.Optional("fetch_pv_forecast", default=True): cv.boolean,
        vol.Optional("fetch_now", default=True): cv.boolean,
    }
)

GLOW_SCHEMA = vol.Schema(
    {
        vol.Required("enabled"): cv.boolean,
        vol.Optional("mqtt_enabled", default=True): cv.boolean,
        vol.Optional("api_enabled", default=True): cv.boolean,
        vol.Optional("username"): vol.Any(str, None),
        vol.Optional("password"): vol.Any(str, None),
        vol.Optional("topic_prefix", default="glow"): str,
        vol.Optional("device_id", default="+"): str,
        vol.Optional("import_resource_id"): vol.Any(str, None),
        vol.Optional("export_resource_id"): vol.Any(str, None),
        vol.Optional("fetch_now", default=True): cv.boolean,
    }
)

TARIFF_DYNAMIC_SCHEMA = vol.Schema(
    {
        vol.Optional("enabled", default=False): cv.boolean,
        vol.Optional("provider", default=""): str,
        vol.Optional("source", default="native"): vol.In(["native", "entity"]),
        vol.Optional("api_key"): vol.Any(str, None),
        vol.Optional("account_number"): vol.Any(str, None),
        vol.Optional("import_mpan"): vol.Any(str, None),
        vol.Optional("export_mpan"): vol.Any(str, None),
        vol.Optional("import_entity"): vol.Any(str, None),
        vol.Optional("export_entity"): vol.Any(str, None),
        vol.Optional("fetch_now", default=True): cv.boolean,
        vol.Optional("apply_schedule", default=False): cv.boolean,
    }
)

TARIFF_RATE_MINOR = vol.All(vol.Coerce(float), vol.Range(min=0, max=999999))

TARIFF_BAND_SCHEMA = vol.Schema(
    {
        vol.Optional("import_p_per_kwh", default=0): TARIFF_RATE_MINOR,
        vol.Optional("export_p_per_kwh", default=0): TARIFF_RATE_MINOR,
    }
)

TARIFF_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional("hours", default=list): cv.ensure_list,
        vol.Optional("bands", default=list): vol.All(cv.ensure_list, [TARIFF_BAND_SCHEMA]),
    }
)

TARIFF_SCHEMA = vol.Schema(
    {
        vol.Optional("kind", default="static"): vol.In(["static", "dynamic"]),
        vol.Optional("currency", default="GBP"): vol.In(sorted(TARIFF_CURRENCIES)),
        vol.Optional("import_source", default="schedule"): vol.In(["manual", "schedule", "entity"]),
        vol.Optional("import_entity", default=None): vol.Any(None, cv.string),
        vol.Required("import_p_per_kwh"): TARIFF_RATE_MINOR,
        vol.Optional("export_source", default="schedule"): vol.In(["manual", "schedule", "entity"]),
        vol.Optional("export_entity", default=None): vol.Any(None, cv.string),
        vol.Required("export_p_per_kwh"): TARIFF_RATE_MINOR,
        vol.Optional("standing_source", default="plugin"): vol.In(["manual", "plugin", "entity"]),
        vol.Optional("standing_entity", default=None): vol.Any(None, cv.string),
        vol.Required("standing_charge_p_per_day"): TARIFF_RATE_MINOR,
        vol.Optional("schedule", default={}): TARIFF_SCHEDULE_SCHEMA,
        vol.Optional("dynamic", default={}): TARIFF_DYNAMIC_SCHEMA,
    }
)


def _get_coordinator(hass: HomeAssistant, plant_id: str | None):
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data:
        return None, "not_found", "No plants configured"
    if plant_id is None:
        if len(domain_data) == 1:
            plant_id = next(iter(domain_data))
        else:
            return None, "invalid_info", "plant_id required"
    if plant_id not in domain_data:
        return None, "not_found", f"Plant {plant_id} not found"
    return domain_data[plant_id]["coordinator"], None, None


def _plant_summary(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    data = hass.data[DOMAIN][entry_id]
    coordinator = data["coordinator"]
    return coordinator.get_plant_state()


def _history_state_to_point(state) -> dict[str, float] | None:
    """Recorder history row as {t, v}; handles State objects and minimal_response dicts."""
    if isinstance(state, dict):
        raw = state.get("state", state.get("s"))
        ts_raw = (
            state.get("last_updated")
            or state.get("last_changed")
            or state.get("lu")
            or state.get("lc")
            or state.get("last_updated_ts")
        )
    else:
        raw = getattr(state, "state", None)
        ts_raw = getattr(state, "last_updated", None) or getattr(state, "last_changed", None)

    if raw in (None, "unknown", "unavailable"):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None

    if ts_raw is None:
        return None
    if isinstance(ts_raw, (int, float)):
        t_ms = float(ts_raw) * 1000 if ts_raw < 1e12 else float(ts_raw)
    else:
        parsed = dt_util.parse_datetime(str(ts_raw))
        if parsed is None:
            return None
        t_ms = dt_util.as_utc(parsed).timestamp() * 1000

    return {"t": t_ms, "v": value}


def _fetch_history_points(
    hass: HomeAssistant,
    start_time: dt,
    end_time: dt,
    entity_ids: list[str],
    significant_changes_only: bool = False,
) -> dict[str, list[dict[str, float]]]:
    """Same recorder query Lovelace history graphs use."""
    with session_scope(hass=hass, read_only=True) as session:
        states_map = history.get_significant_states_with_session(
            hass,
            session,
            start_time,
            end_time,
            entity_ids,
            None,
            include_start_time_state=True,
            significant_changes_only=significant_changes_only,
            minimal_response=True,
            no_attributes=True,
        )
    out: dict[str, list[dict[str, float]]] = {}
    for entity_id in entity_ids:
        points: list[dict[str, float]] = []
        for state in states_map.get(entity_id) or []:
            pt = _history_state_to_point(state)
            if pt is not None:
                points.append(pt)
        out[entity_id] = points
    for entity_id in entity_ids:
        out.setdefault(entity_id, []).sort(key=lambda p: p["t"])
    return out


def _fetch_statistics_points(
    hass: HomeAssistant,
    start_time: dt,
    end_time: dt,
    entity_ids: list[str],
    period: str = "5minute",
    statistic: str = "mean",
) -> dict[str, list[dict[str, float]]]:
    """5-minute (etc.) recorder statistics — same source as plotly-graph cards."""
    from homeassistant.components.recorder.statistics import statistics_during_period

    period_delta = {
        "5minute": timedelta(minutes=5),
        "hour": timedelta(hours=1),
        "day": timedelta(days=1),
    }.get(period, timedelta(minutes=5))
    stat_type = statistic if statistic in ("mean", "min", "max", "sum", "state") else "mean"
    stats = statistics_during_period(
        hass,
        start_time,
        end_time,
        entity_ids,
        period_delta,
        None,
        [stat_type],
    )
    out: dict[str, list[dict[str, float]]] = {entity_id: [] for entity_id in entity_ids}
    for entity_id in entity_ids:
        for row in stats.get(entity_id) or []:
            if isinstance(row, dict):
                value = row.get(stat_type)
                start = row.get("start")
            else:
                value = getattr(row, stat_type, None)
                start = getattr(row, "start", None)
            if value is None:
                continue
            if isinstance(start, (int, float)):
                start_ts = float(start)
            else:
                start_ts = dt_util.as_utc(start).timestamp()
            out[entity_id].append(
                {
                    "start": start_ts,
                    "mean": float(value),
                }
            )
        out[entity_id].sort(key=lambda p: p["start"])
    return out


@callback
def async_register_ws_handlers(hass: HomeAssistant) -> None:
    """Register websocket commands for the panel."""
    if hass.data.get("_foxess_plant_ws_registered"):
        return

    @websocket_api.websocket_command({vol.Required("type"): WS_TYPE_PLANT_LIST})
    @websocket_api.async_response
    async def ws_plant_list(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        plants = []
        for entry_id in hass.data.get(DOMAIN, {}):
            if not isinstance(hass.data[DOMAIN].get(entry_id), dict):
                continue
            try:
                summary = _plant_summary(hass, entry_id)
            except KeyError:
                continue
            plants.append(
                {
                    "entry_id": entry_id,
                    "title": summary.get("title"),
                    "mode": summary.get("mode"),
                    "control_active": summary.get("control_active"),
                }
            )
        connection.send_result(msg["id"], {"plants": plants})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_PLANT_STATE,
            vol.Optional("plant_id"): str,
        }
    )
    @websocket_api.async_response
    async def ws_plant_state(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        plant_id = msg.get("plant_id")
        coordinator, err_code, err_msg = _get_coordinator(hass, plant_id)
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        try:
            await coordinator.async_ensure_solcast_cache(allow_poll=False)
            connection.send_result(msg["id"], coordinator.get_plant_state())
        except Exception as err:
            _LOGGER.exception("plant_state websocket failed")
            connection.send_error(
                msg["id"],
                "plant_state_failed",
                str(err) or err.__class__.__name__,
            )

    @websocket_api.websocket_command({vol.Required("type"): WS_TYPE_TRIGGER_CANDIDATES})
    @websocket_api.async_response
    async def ws_trigger_candidates(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        connection.send_result(msg["id"], list_trigger_candidates(hass))

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_UPDATE_STORM_PREP,
            vol.Optional("plant_id"): str,
            vol.Required("enabled"): cv.boolean,
            vol.Optional("trigger_entities", default=[]): [cv.entity_id],
            vol.Required("charge_periods"): [PERIOD_SCHEMA],
            vol.Optional("target_max_soc"): vol.Any(vol.Coerce(float), None),
            vol.Optional("alert_provider"): vol.In([STORM_ALERT_PROVIDER_GOOGLE]),
            vol.Optional("google_weather_entry_id"): str,
            vol.Optional("use_forecast_lead"): cv.boolean,
            vol.Optional("forecast_lead_hours"): vol.All(vol.Coerce(int), vol.Range(min=1, max=48)),
            vol.Optional("storm_weather_categories"): vol.Any(None, [str]),
            vol.Optional("use_solcast_grid_limit"): cv.boolean,
            vol.Optional("solcast_safety_margin"): vol.All(
                vol.Coerce(float), vol.Range(min=1.0, max=3.0)
            ),
            vol.Optional("solcast_min_soc_floor"): vol.All(
                vol.Coerce(float), vol.Range(min=10, max=100)
            ),
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_update_storm_prep(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        target = msg.get("target_max_soc")
        await coordinator.async_save_storm_prep(
            enabled=msg["enabled"],
            trigger_entities=msg.get("trigger_entities") or [],
            charge_periods=msg["charge_periods"],
            target_max_soc=float(target) if target is not None else None,
            alert_provider=msg.get("alert_provider"),
            google_weather_entry_id=msg.get("google_weather_entry_id"),
            use_forecast_lead=msg.get("use_forecast_lead"),
            forecast_lead_hours=msg.get("forecast_lead_hours"),
            storm_weather_categories=msg.get("storm_weather_categories"),
            use_solcast_grid_limit=msg.get("use_solcast_grid_limit"),
            solcast_safety_margin=msg.get("solcast_safety_margin"),
            solcast_min_soc_floor=msg.get("solcast_min_soc_floor"),
        )
        connection.send_result(msg["id"], coordinator.get_plant_state())

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_SET_SOC_LIMITS,
            vol.Optional("plant_id"): str,
            vol.Required("min_soc"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
            vol.Required("min_soc_on_grid"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
            vol.Required("max_soc"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_set_soc_limits(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        try:
            soc_write_results = await coordinator.async_set_soc_limits(
                msg["min_soc"],
                msg["min_soc_on_grid"],
                msg["max_soc"],
            )
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "soc_save_failed", str(err))
            return
        connection.send_result(
            msg["id"],
            {
                **coordinator.get_plant_state(),
                "soc_write_results": soc_write_results,
            },
        )

    @websocket_api.websocket_command({vol.Required("type"): WS_TYPE_FORECAST_ENTITY_CANDIDATES})
    @websocket_api.async_response
    async def ws_forecast_entity_candidates(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        connection.send_result(
            msg["id"],
            {"entities": list_forecast_entity_candidates(hass)},
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_UPDATE_PANEL_DISPLAY,
            vol.Optional("plant_id"): str,
            vol.Optional("forecast_entity_id"): vol.Any(str, None),
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_update_panel_display(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        raw = msg.get("forecast_entity_id")
        forecast_entity_id = None if raw in (None, "") else str(raw)
        await coordinator.async_save_panel_display(forecast_entity_id=forecast_entity_id)
        connection.send_result(msg["id"], coordinator.get_plant_state())

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_UPDATE_PV_CONFIG,
            vol.Optional("plant_id"): str,
            vol.Required("pv_config"): PV_CONFIG_SCHEMA,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_update_pv_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        await coordinator.async_save_pv_config(pv_config=msg["pv_config"])
        connection.send_result(msg["id"], coordinator.get_plant_state())

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_UPDATE_TARIFF,
            vol.Optional("plant_id"): str,
            vol.Required("tariff"): TARIFF_SCHEMA,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_update_tariff(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        from homeassistant.exceptions import HomeAssistantError

        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        try:
            await coordinator.async_save_tariff(tariff=msg["tariff"])
            connection.send_result(msg["id"], coordinator.get_plant_state())
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "save_failed", str(err))
        except Exception as err:
            _LOGGER.exception("Tariff save failed")
            connection.send_error(msg["id"], "save_failed", str(err) or err.__class__.__name__)

    @websocket_api.websocket_command({vol.Required("type"): WS_TYPE_TARIFF_ENTITY_CANDIDATES})
    @websocket_api.async_response
    async def ws_tariff_entity_candidates(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        connection.send_result(msg["id"], {"entities": list_tariff_entity_candidates(hass)})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_UPDATE_OCTOPUS,
            vol.Optional("plant_id"): str,
            vol.Required("octopus"): TARIFF_DYNAMIC_SCHEMA,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_update_octopus(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        from homeassistant.exceptions import HomeAssistantError

        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        payload = dict(msg["octopus"])
        if payload.get("enabled") and not payload.get("provider"):
            payload["provider"] = "octopus"
        try:
            await coordinator.async_save_octopus(dynamic=payload)
            connection.send_result(msg["id"], coordinator.get_plant_state())
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "save_failed", str(err))
        except Exception as err:
            _LOGGER.exception("Octopus save failed")
            connection.send_error(msg["id"], "save_failed", str(err) or err.__class__.__name__)

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_TEST_OCTOPUS,
            vol.Optional("plant_id"): str,
            vol.Optional("api_key"): str,
            vol.Optional("account_number"): str,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_test_octopus(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        from homeassistant.exceptions import HomeAssistantError

        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        try:
            result = await coordinator.async_test_octopus(
                api_key=msg.get("api_key"),
                account_number=msg.get("account_number"),
            )
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "octopus_test_failed", str(err))
            return
        connection.send_result(
            msg["id"],
            {"octopus": result, "plant_state": coordinator.get_plant_state()},
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_FETCH_OCTOPUS,
            vol.Optional("plant_id"): str,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_fetch_octopus(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        from homeassistant.exceptions import HomeAssistantError

        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        try:
            octopus = await coordinator.async_fetch_octopus()
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "octopus_fetch_failed", str(err))
            return
        connection.send_result(
            msg["id"],
            {"octopus": octopus, "plant_state": coordinator.get_plant_state()},
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_FETCH_OCTOPUS_ANALYSIS,
            vol.Optional("plant_id"): str,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_fetch_octopus_analysis(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        try:
            analysis = await coordinator.async_fetch_octopus_analysis(
                force=bool(msg.get("force"))
            )
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "octopus_analysis_fetch_failed", str(err))
            return
        connection.send_result(
            msg["id"],
            {"octopus_analysis": analysis, "plant_state": coordinator.get_plant_state()},
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_APPLY_OCTOPUS_SCHEDULE,
            vol.Optional("plant_id"): str,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_apply_octopus_schedule(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        from homeassistant.exceptions import HomeAssistantError

        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        try:
            tariff = await coordinator.async_apply_octopus_schedule()
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "apply_failed", str(err))
            return
        connection.send_result(
            msg["id"],
            {"tariff": tariff, "plant_state": coordinator.get_plant_state()},
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_UPDATE_SMART_CHARGE,
            vol.Optional("plant_id"): str,
            vol.Required("enabled"): cv.boolean,
            vol.Optional("target_soc", default=100.0): vol.All(vol.Coerce(float), vol.Range(min=10, max=100)),
            vol.Optional("target_max_soc"): vol.Any(vol.Coerce(float), None),
            vol.Optional("max_target_soc", default=100.0): vol.All(vol.Coerce(float), vol.Range(min=10, max=100)),
            vol.Optional("min_deficit_kwh", default=0.5): vol.All(vol.Coerce(float), vol.Range(min=0, max=50)),
            vol.Optional("solar_safety_margin", default=1.15): vol.All(
                vol.Coerce(float), vol.Range(min=1.0, max=3.0)
            ),
            vol.Optional("round_trip_efficiency", default=0.9): vol.All(
                vol.Coerce(float), vol.Range(min=0.5, max=1.0)
            ),
            vol.Optional("min_arbitrage_p_per_kwh", default=0.5): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=50)
            ),
            vol.Optional("operating_mode", default="max_safety"): vol.In(
                ("max_profit", "max_safety", "max_green")
            ),
            vol.Optional("agile_poll_interval_minutes", default=15): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=60)
            ),
            vol.Optional("negative_import_interrupt", default=True): cv.boolean,
            vol.Optional("price_drop_interrupt_p_per_kwh", default=2.0): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=50)
            ),
            vol.Optional("daily_plan_time", default="16:00"): cv.string,
            vol.Optional("daily_plan_horizon_hours", default=24): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=48)
            ),
            vol.Optional("house_load_kw_fallback", default=1.0): vol.All(
                vol.Coerce(float), vol.Range(min=0.1, max=50)
            ),
            vol.Optional("dark_hours_estimate", default=8.0): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=24)
            ),
            vol.Optional("outage_reserve_load_kw"): vol.Any(vol.Coerce(float), None),
            vol.Optional("outage_reserve_hours", default=3.0): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=24)
            ),
            vol.Optional("outage_reserve_margin", default=1.2): vol.All(
                vol.Coerce(float), vol.Range(min=1.0, max=5.0)
            ),
            vol.Optional("safety_reserve_multiplier", default=1.5): vol.All(
                vol.Coerce(float), vol.Range(min=1.0, max=5.0)
            ),
            vol.Optional("green_carbon_weight", default=0.5): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=1.0)
            ),
            vol.Optional("export_enabled", default=True): cv.boolean,
            vol.Optional("export_enabled_safety", default=True): cv.boolean,
            vol.Optional("export_enabled_green", default=False): cv.boolean,
            vol.Optional("min_export_kwh", default=0.5): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=50)),
            vol.Optional("min_export_p_profit", default=12.0): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=100)
            ),
            vol.Optional("min_export_p_safety", default=20.0): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=100)
            ),
            vol.Optional("min_export_p_green", default=25.0): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=100)
            ),
            vol.Optional("exportable_fraction_profit", default=1.0): vol.All(
                vol.Coerce(float), vol.Range(min=0.05, max=1.0)
            ),
            vol.Optional("exportable_fraction_safety", default=0.35): vol.All(
                vol.Coerce(float), vol.Range(min=0.05, max=1.0)
            ),
            vol.Optional("exportable_fraction_green", default=0.15): vol.All(
                vol.Coerce(float), vol.Range(min=0.05, max=1.0)
            ),
            vol.Optional("spread_optimizer_enabled", default=True): cv.boolean,
            vol.Optional("min_spread_profit_p_per_kwh", default=3.0): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=50)
            ),
            vol.Optional("peak_import_avoid_start", default="16:00"): cv.string,
            vol.Optional("peak_import_avoid_end", default="19:00"): cv.string,
            vol.Optional("winter_fill_enabled", default=True): cv.boolean,
            vol.Optional("green_export_spread_multiplier", default=2.0): vol.All(
                vol.Coerce(float), vol.Range(min=1, max=10)
            ),
            vol.Optional("cheap_import_p_per_kwh", default=8.0): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=50)
            ),
            vol.Optional("peak_import_penalty_p_per_kwh", default=5.0): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=50)
            ),
            vol.Required("charge_periods"): [PERIOD_SCHEMA],
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_update_smart_charge(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        payload = {
            key: msg[key]
            for key in (
                "enabled",
                "target_soc",
                "target_max_soc",
                "max_target_soc",
                "min_deficit_kwh",
                "solar_safety_margin",
                "round_trip_efficiency",
                "min_arbitrage_p_per_kwh",
                "operating_mode",
                "agile_poll_interval_minutes",
                "negative_import_interrupt",
                "price_drop_interrupt_p_per_kwh",
                "daily_plan_time",
                "daily_plan_horizon_hours",
                "house_load_kw_fallback",
                "dark_hours_estimate",
                "outage_reserve_load_kw",
                "outage_reserve_hours",
                "outage_reserve_margin",
                "safety_reserve_multiplier",
                "green_carbon_weight",
                "export_enabled",
                "export_enabled_safety",
                "export_enabled_green",
                "min_export_kwh",
                "min_export_p_profit",
                "min_export_p_safety",
                "min_export_p_green",
                "exportable_fraction_profit",
                "exportable_fraction_safety",
                "exportable_fraction_green",
                "spread_optimizer_enabled",
                "min_spread_profit_p_per_kwh",
                "peak_import_avoid_start",
                "peak_import_avoid_end",
                "winter_fill_enabled",
                "green_export_spread_multiplier",
                "cheap_import_p_per_kwh",
                "peak_import_penalty_p_per_kwh",
                "charge_periods",
            )
            if key in msg
        }
        await coordinator.async_save_smart_charge(smart_charge=payload)
        connection.send_result(msg["id"], coordinator.get_plant_state())

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_UPDATE_SOLCAST,
            vol.Optional("plant_id"): str,
            vol.Required("solcast"): SOLCAST_SCHEMA,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_update_solcast(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        payload = dict(msg["solcast"])
        fetch_now = bool(payload.pop("fetch_now", True))
        await coordinator.async_save_solcast(solcast=payload, fetch_now=fetch_now)
        connection.send_result(msg["id"], coordinator.get_plant_state())

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_TEST_SOLCAST,
            vol.Optional("plant_id"): str,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_test_solcast(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        try:
            result = await coordinator.async_test_solcast()
        except Exception as err:
            connection.send_error(msg["id"], "solcast_test_failed", str(err))
            return
        connection.send_result(msg["id"], {"solcast": result, "plant_state": coordinator.get_plant_state()})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_UPDATE_GLOW,
            vol.Optional("plant_id"): str,
            vol.Required("glow"): GLOW_SCHEMA,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_update_glow(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        payload = dict(msg["glow"])
        fetch_now = bool(payload.pop("fetch_now", True))
        try:
            await coordinator.async_save_glow(glow=payload, fetch_now=fetch_now)
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "glow_save_failed", str(err))
            return
        connection.send_result(msg["id"], coordinator.get_plant_state())

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_TEST_GLOW,
            vol.Optional("plant_id"): str,
            vol.Optional("username"): str,
            vol.Optional("password"): str,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_test_glow(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        try:
            result = await coordinator.async_test_glow(
                username=msg.get("username"),
                password=msg.get("password"),
            )
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "glow_test_failed", str(err))
            return
        except Exception as err:
            connection.send_error(msg["id"], "glow_test_failed", str(err))
            return
        connection.send_result(msg["id"], {"glow": result, "plant_state": coordinator.get_plant_state()})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_FETCH_HISTORY,
            vol.Required("start_time"): str,
            vol.Optional("end_time"): str,
            vol.Required("entity_ids"): [cv.entity_id],
            vol.Optional("significant_changes_only", default=False): bool,
        }
    )
    @websocket_api.async_response
    async def ws_fetch_history(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        start = dt_util.parse_datetime(msg["start_time"])
        if start is None:
            connection.send_error(msg["id"], "invalid_start", "Invalid start_time")
            return
        end_raw = msg.get("end_time")
        end = dt_util.parse_datetime(end_raw) if end_raw else dt_util.utcnow()
        if end is None:
            connection.send_error(msg["id"], "invalid_end", "Invalid end_time")
            return
        start_utc = dt_util.as_utc(start)
        end_utc = dt_util.as_utc(end)
        entity_ids = list(msg["entity_ids"])
        try:
            result = await hass.async_add_executor_job(
                partial(
                    _fetch_history_points,
                    hass,
                    start_utc,
                    end_utc,
                    entity_ids,
                    significant_changes_only=msg.get("significant_changes_only", False),
                )
            )
        except Exception as err:
            _LOGGER.exception("fetch_history failed for %s", entity_ids)
            connection.send_error(msg["id"], "fetch_history_failed", str(err))
            return
        connection.send_result(msg["id"], result)

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_FETCH_STATISTICS,
            vol.Required("start_time"): str,
            vol.Optional("end_time"): str,
            vol.Required("entity_ids"): [cv.entity_id],
            vol.Optional("period", default="5minute"): vol.In(("5minute", "hour", "day")),
            vol.Optional("statistic", default="mean"): vol.In(("mean", "min", "max", "sum", "state")),
        }
    )
    @websocket_api.async_response
    async def ws_fetch_statistics(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        start = dt_util.parse_datetime(msg["start_time"])
        if start is None:
            connection.send_error(msg["id"], "invalid_start", "Invalid start_time")
            return
        end_raw = msg.get("end_time")
        end = dt_util.parse_datetime(end_raw) if end_raw else dt_util.utcnow()
        if end is None:
            connection.send_error(msg["id"], "invalid_end", "Invalid end_time")
            return
        start_utc = dt_util.as_utc(start)
        end_utc = dt_util.as_utc(end)
        entity_ids = list(msg["entity_ids"])
        try:
            result = await hass.async_add_executor_job(
                partial(
                    _fetch_statistics_points,
                    hass,
                    start_utc,
                    end_utc,
                    entity_ids,
                    period=msg.get("period", "5minute"),
                    statistic=msg.get("statistic", "mean"),
                )
            )
        except Exception as err:
            _LOGGER.exception("fetch_statistics failed for %s", entity_ids)
            connection.send_error(msg["id"], "fetch_statistics_failed", str(err))
            return
        connection.send_result(msg["id"], result)

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_SOLCAST_FORECAST_INTRADAY,
            vol.Required("plant_id"): str,
            vol.Optional("day"): str,
        }
    )
    @websocket_api.async_response
    async def ws_solcast_forecast_intraday(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        day_raw = msg.get("day")
        if day_raw:
            target_day = dt_util.parse_date(str(day_raw))
            if target_day is None:
                connection.send_error(msg["id"], "invalid_day", "Invalid day (use YYYY-MM-DD)")
                return
        else:
            target_day = dt_util.as_local(dt_util.utcnow()).date()
        from .solcast_forecast_chart import (
            build_forecast_intraday_chart,
            build_forecast_intraday_chart_for_day,
        )

        try:
            stored = await coordinator.async_read_solcast_stored()
            local_today = dt_util.as_local(dt_util.utcnow()).date()
            if target_day == local_today:
                await coordinator.async_ensure_solcast_cache(allow_poll=False)
                if len(coordinator._solcast_forecast_chart_points) < 2:
                    await coordinator._rebuild_solcast_forecast_chart(stored=stored)
                points = list(coordinator._solcast_forecast_chart_points)
                if len(points) < 2:
                    points = build_forecast_intraday_chart(
                        hass,
                        stored,
                        coordinator._solcast_cache,
                        entry_id=coordinator.config_entry.entry_id,
                        memory_snapshots=list(coordinator._solcast_memory_snapshots),
                    )
            else:
                job = partial(
                    build_forecast_intraday_chart_for_day,
                    hass,
                    stored,
                    coordinator._solcast_cache,
                    target_day,
                    entry_id=coordinator.config_entry.entry_id,
                )
                points = await get_instance(hass).async_add_executor_job(job)
        except Exception as err:
            _LOGGER.exception("solcast_forecast_intraday failed for %s", target_day.isoformat())
            connection.send_error(
                msg["id"],
                "forecast_intraday_failed",
                str(err) or "Forecast intraday chart failed",
            )
            return
        connection.send_result(msg["id"], {"points": points, "day": target_day.isoformat()})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_SOLCAST_STATISTICS_FORECAST,
            vol.Required("plant_id"): str,
        }
    )
    @websocket_api.async_response
    async def ws_solcast_statistics_forecast(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        from .solcast_forecast_chart import build_statistics_forecast_overlay

        try:
            await coordinator.async_ensure_solcast_cache(allow_poll=False)
            stored = await coordinator.async_read_solcast_stored()
            if len(coordinator._solcast_forecast_chart_points) < 2:
                await coordinator._rebuild_solcast_forecast_chart(stored=stored)

            points = build_statistics_forecast_overlay(
                hass,
                stored,
                coordinator._solcast_cache,
                entry_id=coordinator.config_entry.entry_id,
                memory_snapshots=list(coordinator._solcast_memory_snapshots),
            )
        except Exception as err:
            _LOGGER.exception("solcast_statistics_forecast failed")
            connection.send_error(
                msg["id"],
                "statistics_forecast_failed",
                str(err) or "Statistics forecast overlay failed",
            )
            return
        connection.send_result(msg["id"], {"points": points})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): WS_TYPE_SOLCAST_FORECAST_ACCURACY,
            vol.Required("plant_id"): str,
            vol.Optional("day"): str,
        }
    )
    @websocket_api.async_response
    async def ws_solcast_forecast_accuracy(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        coordinator, err_code, err_msg = _get_coordinator(hass, msg.get("plant_id"))
        if coordinator is None:
            connection.send_error(msg["id"], err_code, err_msg)
            return
        day_raw = msg.get("day")
        if day_raw:
            target_day = dt_util.parse_date(str(day_raw))
            if target_day is None:
                connection.send_error(msg["id"], "invalid_day", "Invalid day (use YYYY-MM-DD)")
                return
        else:
            target_day = dt_util.as_local(dt_util.utcnow()).date()
        from .solcast_forecast_accuracy import build_forecast_accuracy_report

        try:
            await coordinator.async_ensure_solcast_cache(allow_poll=False)
            stored = await coordinator.async_read_solcast_stored()
            job = partial(
                build_forecast_accuracy_report,
                hass,
                stored,
                coordinator._solcast_cache,
                coordinator.plant.entity_map,
                target_day,
                entry_id=coordinator.config_entry.entry_id,
                storm_prep=coordinator.plant.storm_prep,
                memory_snapshots=list(coordinator._solcast_memory_snapshots),
            )
            report = await get_instance(hass).async_add_executor_job(job)
        except Exception as err:
            _LOGGER.exception("solcast_forecast_accuracy failed for %s", target_day.isoformat())
            report = {
                "error": str(err) or type(err).__name__ or "Forecast accuracy report failed",
                "solcast_enabled": True,
                "day": target_day.isoformat(),
            }
        connection.send_result(msg["id"], report)

    websocket_api.async_register_command(hass, ws_plant_list)
    websocket_api.async_register_command(hass, ws_plant_state)
    websocket_api.async_register_command(hass, ws_trigger_candidates)
    websocket_api.async_register_command(hass, ws_update_storm_prep)
    websocket_api.async_register_command(hass, ws_set_soc_limits)
    websocket_api.async_register_command(hass, ws_forecast_entity_candidates)
    websocket_api.async_register_command(hass, ws_update_panel_display)
    websocket_api.async_register_command(hass, ws_update_pv_config)
    websocket_api.async_register_command(hass, ws_update_tariff)
    websocket_api.async_register_command(hass, ws_tariff_entity_candidates)
    websocket_api.async_register_command(hass, ws_update_octopus)
    websocket_api.async_register_command(hass, ws_test_octopus)
    websocket_api.async_register_command(hass, ws_fetch_octopus)
    websocket_api.async_register_command(hass, ws_fetch_octopus_analysis)
    websocket_api.async_register_command(hass, ws_apply_octopus_schedule)
    websocket_api.async_register_command(hass, ws_update_smart_charge)
    websocket_api.async_register_command(hass, ws_update_solcast)
    websocket_api.async_register_command(hass, ws_test_solcast)
    websocket_api.async_register_command(hass, ws_update_glow)
    websocket_api.async_register_command(hass, ws_test_glow)
    websocket_api.async_register_command(hass, ws_fetch_history)
    websocket_api.async_register_command(hass, ws_fetch_statistics)
    websocket_api.async_register_command(hass, ws_solcast_forecast_intraday)
    websocket_api.async_register_command(hass, ws_solcast_forecast_accuracy)
    websocket_api.async_register_command(hass, ws_solcast_statistics_forecast)
    hass.data["_foxess_plant_ws_registered"] = True
