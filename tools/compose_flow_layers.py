#!/usr/bin/env python3
"""Bake flow_pv and flow_aio sprites onto 1024×1017 transparent canvases (Fox scene coords)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
CANVAS = (1024, 1017)

# Fractions of 1024×1017 — tune here, then re-run: python tools/compose_flow_layers.py
BOXES = {
    "pv": {"left": 0.468, "top": 0.318, "width": 0.204, "height": 0.098},
    "aio": {"left": 0.098, "top": 0.598, "width": 0.132, "height": 0.168},
}


def box_pixels(box: dict) -> tuple[int, int, int, int]:
    w, h = CANVAS
    left = int(box["left"] * w)
    top = int(box["top"] * h)
    width = int(box["width"] * w)
    height = int(box["height"] * h)
    return left, top, width, height


def place_sprite(theme: str, layer: str) -> None:
    src_name = f"flow_{layer}" if layer == "pv" else "flow_aio_812"
    src = WWW / f"{src_name}_{theme}.png"
    out = WWW / f"flow_{layer}_scene_{theme}.png"
    sprite = Image.open(src).convert("RGBA")
    left, top, bw, bh = box_pixels(BOXES[layer])
    fitted = sprite.resize((bw, bh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.paste(fitted, (left, top), fitted)
    canvas.save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes)")


def main() -> None:
    for theme in ("day_light", "night_dark"):
        place_sprite(theme, "pv")
        place_sprite(theme, "aio")


if __name__ == "__main__":
    main()
