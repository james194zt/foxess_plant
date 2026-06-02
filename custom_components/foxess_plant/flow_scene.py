"""Resolve flow-scene background theme from Home Assistant sun times."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

FLOW_SCENE_THEME_PEAK = "day_light"
FLOW_SCENE_THEME_SUNRISE = "day_dark"
FLOW_SCENE_THEME_DUSK = "night_light"
FLOW_SCENE_THEME_NIGHT = "night_dark"

FLOW_SCENE_THEMES = frozenset(
    {
        FLOW_SCENE_THEME_PEAK,
        FLOW_SCENE_THEME_SUNRISE,
        FLOW_SCENE_THEME_DUSK,
        FLOW_SCENE_THEME_NIGHT,
    }
)


def _parse_next_sun_event(attrs: dict, key: str):
    raw = attrs.get(f"next_{key}")
    if not raw:
        return None
    return dt_util.parse_datetime(raw)


def _prev_next_sun(attrs: dict, key: str) -> tuple | None:
    parsed = _parse_next_sun_event(attrs, key)
    if parsed is None:
        return None
    nxt = dt_util.as_local(parsed)
    return nxt - timedelta(days=1), nxt


def _last_sun_event(attrs: dict, key: str, now) -> object | None:
    """Most recent occurrence of a sun event at or before *now*."""
    pair = _prev_next_sun(attrs, key)
    if pair is None:
        return None
    prev, nxt = pair
    return nxt if now >= nxt else prev


def _next_sun_event(attrs: dict, key: str, now) -> object | None:
    """Next occurrence of a sun event strictly after *now* (may be later today)."""
    pair = _prev_next_sun(attrs, key)
    if pair is None:
        return None
    _prev, nxt = pair
    return (nxt + timedelta(days=1)) if now >= nxt else nxt


def resolve_flow_scene_theme(hass: HomeAssistant) -> str:
    """Map current time to a flow background theme using ``sun.sun`` attributes."""
    sun = hass.states.get("sun.sun")
    if not sun or sun.state in ("unknown", "unavailable"):
        return FLOW_SCENE_THEME_PEAK

    now = dt_util.now()
    attrs = sun.attributes
    last_dawn = _last_sun_event(attrs, "dawn", now)
    last_rising = _last_sun_event(attrs, "rising", now)
    last_setting = _last_sun_event(attrs, "setting", now)
    last_dusk = _last_sun_event(attrs, "dusk", now)
    next_setting = _next_sun_event(attrs, "setting", now)

    if None in (last_dawn, last_rising, last_setting, last_dusk, next_setting):
        return FLOW_SCENE_THEME_PEAK

    if last_dawn <= now < last_rising:
        return FLOW_SCENE_THEME_SUNRISE
    if last_rising <= now < next_setting:
        return FLOW_SCENE_THEME_PEAK
    if last_setting <= now < last_dusk:
        return FLOW_SCENE_THEME_DUSK
    return FLOW_SCENE_THEME_NIGHT
