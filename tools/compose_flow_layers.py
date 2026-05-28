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
    "pv": {"left": 0.388, "top": 0.342, "width": 0.425, "height": 0.228},
    "aio": {"left": 0.312, "top": 0.610, "width": 0.136, "height": 0.222},
}


def box_pixels(box: dict) -> tuple[int, int, int, int]:
    w, h = CANVAS
    left = int(box["left"] * w)
    top = int(box["top"] * h)
    width = int(box["width"] * w)
    height = int(box["height"] * h)
    return left, top, width, height


def derive_anchors() -> dict[str, tuple[int, int]]:
    pv_l, pv_t, pv_w, pv_h = box_pixels(BOXES["pv"])
    aio_l, aio_t, aio_w, aio_h = box_pixels(BOXES["aio"])
    solar_x = pv_l + pv_w // 2
    aio_x = aio_l + aio_w // 2
    return {
        "solar_label": (solar_x, 92),
        "solar_top": (solar_x, pv_t),
        "solar_base": (solar_x, pv_t + pv_h),
        "aio_top": (aio_x, aio_t + int(aio_h * 0.12)),
        "aio_mid": (aio_x, aio_t + aio_h // 2),
        "hub": (512, 752),
        "home": (678, 578),
        "grid": (228, 788),
    }


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
    a = derive_anchors()
    print("anchors", a)
    print(
        "paths:",
        f'solar-drop M {a["solar_label"][0]} {a["solar_label"][1]} L {a["solar_top"][0]} {a["solar_top"][1]}',
        f'solar-aio M {a["aio_top"][0]} {a["solar_top"][1]} L {a["aio_mid"][0]} {a["aio_mid"][1]}',
    )


if __name__ == "__main__":
    main()
