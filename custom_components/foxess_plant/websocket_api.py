"""WebSocket API for the Fox Plant panel."""

from __future__ import annotations

from datetime import datetime as dt, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.recorder import get_instance, history
from homeassistant.components.recorder.util import session_scope
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STORM_ALERT_PROVIDER_GOOGLE
from .panel_config import list_forecast_entity_candidates, list_trigger_candidates

WS_TYPE_PLANT_STATE = "foxess_plant/plant_state"
WS_TYPE_PLANT_LIST = "foxess_plant/plant_list"
WS_TYPE_TRIGGER_CANDIDATES = "foxess_plant/trigger_candidates"
WS_TYPE_UPDATE_STORM_PREP = "foxess_plant/update_storm_prep"
WS_TYPE_SET_SOC_LIMITS = "foxess_plant/set_soc_limits"
WS_TYPE_FORECAST_ENTITY_CANDIDATES = "foxess_plant/forecast_entity_candidates"
WS_TYPE_UPDATE_PANEL_DISPLAY = "foxess_plant/update_panel_display"
WS_TYPE_FETCH_HISTORY = "foxess_plant/fetch_history"
WS_TYPE_FETCH_STATISTICS = "foxess_plant/fetch_statistics"

PERIOD_SCHEMA = vol.Schema(
    {
        vol.Required("enable_force_charge"): cv.boolean,
        vol.Required("enable_charge_from_grid"): cv.boolean,
        vol.Optional("start", default="00:00"): cv.string,
        vol.Optional("end", default="00:00"): cv.string,
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


def _fetch_history_points(
    hass: HomeAssistant,
    start_time: dt,
    end_time: dt,
    entity_ids: list[str],
    *,
    significant_changes_only: bool,
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
            try:
                value = float(state.state)
            except (TypeError, ValueError):
                continue
            points.append(
                {
                    "t": state.last_updated.timestamp() * 1000,
                    "v": value,
                }
            )
        out[entity_id] = points
    for entity_id in entity_ids:
        out.setdefault(entity_id, []).sort(key=lambda p: p["t"])
    return out


def _fetch_statistics_points(
    hass: HomeAssistant,
    start_time: dt,
    end_time: dt,
    entity_ids: list[str],
    *,
    period: str,
    statistic: str,
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
        connection.send_result(msg["id"], _plant_summary(hass, coordinator.config_entry.entry_id))

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
        await coordinator.async_set_soc_limits(
            msg["min_soc"],
            msg["min_soc_on_grid"],
            msg["max_soc"],
        )
        connection.send_result(msg["id"], coordinator.get_plant_state())

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
        result = await get_instance(hass).async_add_executor_job(
            _fetch_history_points,
            hass,
            start_utc,
            end_utc,
            entity_ids,
            msg.get("significant_changes_only", False),
        )
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
        result = await get_instance(hass).async_add_executor_job(
            _fetch_statistics_points,
            hass,
            start_utc,
            end_utc,
            entity_ids,
            period=msg.get("period", "5minute"),
            statistic=msg.get("statistic", "mean"),
        )
        connection.send_result(msg["id"], result)

    websocket_api.async_register_command(hass, ws_plant_list)
    websocket_api.async_register_command(hass, ws_plant_state)
    websocket_api.async_register_command(hass, ws_trigger_candidates)
    websocket_api.async_register_command(hass, ws_update_storm_prep)
    websocket_api.async_register_command(hass, ws_set_soc_limits)
    websocket_api.async_register_command(hass, ws_forecast_entity_candidates)
    websocket_api.async_register_command(hass, ws_update_panel_display)
    websocket_api.async_register_command(hass, ws_fetch_history)
    websocket_api.async_register_command(hass, ws_fetch_statistics)
    hass.data["_foxess_plant_ws_registered"] = True
