"""Resolve flow-scene background theme from Home Assistant sun times."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# Fox flow art uses Android *dark* UI theme variants only (_day_dark / _night_dark).
# The _light suffix is for Fox app light mode, not time-of-day.
FLOW_SCENE_THEME_DAY = "day_dark"
FLOW_SCENE_THEME_NIGHT = "night_dark"

FLOW_SCENE_THEMES = frozenset({FLOW_SCENE_THEME_DAY, FLOW_SCENE_THEME_NIGHT})


def resolve_flow_scene_theme(hass: HomeAssistant) -> str:
    """Daylight → day_dark art; otherwise night_dark (Fox app dark-theme assets)."""
    sun = hass.states.get("sun.sun")
    if not sun or sun.state in ("unknown", "unavailable"):
        return FLOW_SCENE_THEME_DAY

    if sun.state == "above_horizon":
        return FLOW_SCENE_THEME_DAY
    return FLOW_SCENE_THEME_NIGHT
