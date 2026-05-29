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
    "pv": {"left": 0.388, "top": 0.342, "width": 0.448, "height": 0.242},
    "aio": {"left": 0.312, "top": 0.622, "width": 0.136, "height": 0.222},
}

# Scene anchors (viewBox 0 0 1024 1017) — tune to match the house render
HUB = (438, 728)  # front-left corner (left wall ⊗ front facade)
WINDOW = (558, 532)  # centre of large front window
GRID = (228, 788)  # grid badge / ground connection (left)


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
        "aio_x": aio_x,
        "window": WINDOW,
        "hub": HUB,
        "home": (678, 578),
        "grid": GRID,
    }


def flow_paths(anchors: dict[str, tuple[int, int]]) -> dict[str, str]:
    """Orthogonal paths: window→hub, AIO→hub along base, hub↓→ground→grid."""
    sx, sy = anchors["solar_label"]
    stx, sty = anchors["solar_top"]
    ax = anchors["aio_x"]
    aty = anchors["aio_top"][1]
    wx, wy = anchors["window"]
    hx, hy = anchors["hub"]
    gx, gy = anchors["grid"]
    return {
        "solar-drop": f"M {sx} {sy} L {stx} {sty}",
        "solar-aio": f"M {ax} {sty} L {ax} {aty}",
        # Grid: along ground to below hub, then up to corner hub
        "grid-hub": f"M {gx} {gy} L {hx} {gy} L {hx} {hy}",
        "hub-grid": f"M {hx} {hy} L {hx} {gy} L {gx} {gy}",
        # AIO: horizontal along house base to corner hub
        "aio-hub": f"M {ax} {hy} L {hx} {hy}",
        "hub-aio": f"M {hx} {hy} L {ax} {hy}",
        # Home: window → corner (across then down)
        "hub-home": f"M {wx} {wy} L {hx} {wy} L {hx} {hy}",
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
    paths = flow_paths(a)
    print("anchors", a)
    print("FOX_FLOW_HUB", f"{{ x: {a['hub'][0]}, y: {a['hub'][1]} }};")
    print("FOX_FLOW_PATHS", paths)


if __name__ == "__main__":
    main()
