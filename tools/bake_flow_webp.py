#!/usr/bin/env python3
"""Encode the Overview flow-scene layers as WebP (what the panel and card load).

The PNGs stay the source of truth for the other bake_* tools; rerun this after
re-baking any flow_*_scene_*.png, then bump FLOW_SCENE_ASSET_VER in
foxess-plant-panel.js and fox-flow-scene-card.js.

Backdrop PNGs are ~850 KB each; at q90 the WebP is ~40 KB. Overlays keep exact
alpha (WebP alpha is lossless by default) so the house edges stay crisp.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

WWW = Path(__file__).resolve().parents[1] / "custom_components" / "foxess_plant" / "www"
THEMES = ("day_dark", "day_light", "night_dark", "night_light")
# layer file stem -> encoder options
LAYERS = {
    "flow_home_bg_scene": {"quality": 90},
    "flow_pv_scene": {"quality": 90},
    "flow_aio_scene": {"lossless": True},
}


def main() -> None:
    for stem, opts in LAYERS.items():
        for theme in THEMES:
            src = WWW / f"{stem}_{theme}.png"
            out = src.with_suffix(".webp")
            img = Image.open(src)
            img.save(out, format="WEBP", method=6, **opts)
            print(f"{out.name}: {src.stat().st_size} -> {out.stat().st_size} bytes")


if __name__ == "__main__":
    main()
