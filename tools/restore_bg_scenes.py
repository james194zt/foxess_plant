#!/usr/bin/env python3
"""Restore flow_home_bg_scene_* from a known-good git commit (v0.8.87 / c4f03c2).

The Fox look comes from this bake: full flow_home_bg + flow_home (black matte only).
Do not use luminance_matte, sky crop, or CSS sky — those break the day bleed.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
REV = "c4f03c2"

for theme in ("day_light", "day_dark", "night_light", "night_dark"):
    blob = subprocess.check_output(
        ["git", "show", f"{REV}:custom_components/foxess_plant/www/flow_home_bg_scene_{theme}.png"],
        cwd=ROOT,
    )
    out = WWW / f"flow_home_bg_scene_{theme}.png"
    out.write_bytes(blob)
    print(f"restored {out.name} ({len(blob)} bytes) from {REV}")
