#!/usr/bin/env python3
"""Decode misnamed flow_pv WEBP files to real PNG sprites."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"

for theme in ("day_light", "night_dark"):
    src = WWW / f"flow_pv_{theme}.png"
    out = WWW / f"flow_pv_{theme}_decoded.png"
    if not src.is_file():
        print(f"skip {src.name}")
        continue
    im = Image.open(src)
    im.save(out, optimize=True)
    print(f"decoded {src.name} -> {out.name} {im.size} {im.mode}")
