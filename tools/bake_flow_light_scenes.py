#!/usr/bin/env python3
"""Re-bake flow_home_bg_scene for _light themes on white canvas."""
from key_flow_home_sky import bake_bg_scene

for theme in ("day_light", "night_light"):
    bake_bg_scene(theme)
