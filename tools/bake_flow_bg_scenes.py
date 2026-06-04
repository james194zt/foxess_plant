#!/usr/bin/env python3
"""Bake flow_home_bg_scene_* (sky + house) for the panel backdrop — matches Fox app."""

from __future__ import annotations

from key_flow_home_sky import FLOW_THEMES, bake_bg_scene

if __name__ == "__main__":
    for theme in FLOW_THEMES:
        bake_bg_scene(theme)
