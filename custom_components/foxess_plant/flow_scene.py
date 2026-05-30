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

_SUN_EVENT_KEYS = ("dawn", "rising", "setting", "dusk")


def _parse_next_sun_event(attrs: dict, key: str):
    raw = attrs.get(f"next_{key}")
    if not raw:
        return None
    return dt_util.parse_datetime(raw)


def _effective_sun_event(attrs: dict, key: str, now):
    """Most recent occurrence of a sun event at or before *now* (local time)."""
    parsed = _parse_next_sun_event(attrs, key)
    if parsed is None:
        return None
    event = dt_util.as_local(parsed)
    while event > now:
        event -= timedelta(days=1)
    return event


def resolve_flow_scene_theme(hass: HomeAssistant) -> str:
    """Map current time to a flow background theme using ``sun.sun`` attributes."""
    sun = hass.states.get("sun.sun")
    if not sun or sun.state in ("unknown", "unavailable"):
        return FLOW_SCENE_THEME_PEAK

    now = dt_util.now()
    attrs = sun.attributes
    dawn = _effective_sun_event(attrs, "dawn", now)
    rising = _effective_sun_event(attrs, "rising", now)
    setting = _effective_sun_event(attrs, "setting", now)
    dusk = _effective_sun_event(attrs, "dusk", now)

    if None in (dawn, rising, setting, dusk):
        return FLOW_SCENE_THEME_PEAK

    if dawn <= now < rising:
        return FLOW_SCENE_THEME_SUNRISE
    if rising <= now < setting:
        return FLOW_SCENE_THEME_PEAK
    if setting <= now < dusk:
        return FLOW_SCENE_THEME_DUSK
    return FLOW_SCENE_THEME_NIGHT
