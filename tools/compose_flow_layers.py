#!/usr/bin/env python3
"""Bake flow_pv and flow_aio sprites onto 1024×1017 transparent canvases (Fox scene coords)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from flow_scene_place import AIO_CONNECT, render_aio_layer, render_pv_layer
from key_flow_home_sky import remove_black_matte

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
CANVAS = (1024, 1017)

# Fractions of 1024×1017 — tune here, then re-run: python tools/compose_flow_layers.py
BOXES = {
    "pv": {"left": 0.388, "top": 0.342, "width": 0.448, "height": 0.242},
    "aio": {"left": 0.312, "top": 0.622, "width": 0.136, "height": 0.222},
}

# Scene anchors (viewBox 0 0 1024 1017)
# LOCKED (v0.8.47): HUB was hand-tuned on the side/front wall corner — do NOT change
# coordinates unless the user explicitly asks. Sync FOX_FLOW_HUB / FOX_FLOW_PATHS in panel JS.
HUB = (536, 726)
# Side-face x at hub row; y derived parallel to hub-home / house base (28px rise per 100px run)
AIO_FACE_X = AIO_CONNECT[0]
WINDOW = (558, 532)  # centre of large front window
WINDOW_EDGE = (636, 698)  # frame corner — full diagonal from hub (~16deg for 3D wall)
GRID = (228, 788)  # grid badge anchor (left)
GROUND_Y = 848  # visible pavement below house base
# Roof line on flow_home art (1024×1017) — solar paths stop here, not above the ridge
SOLAR_LABEL_Y = 92
SOLAR_ROOF_Y = {626: 354, 388: 406}  # just under ridge at each solar spoke x


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
    aio_edge = aio_l + aio_w  # right edge of AIO placement box
    aio_connect = AIO_CONNECT  # tap visible AIO face (pixel-tuned on flow_aio_scene)
    solar_roof_y = SOLAR_ROOF_Y.get(solar_x, pv_t)
    aio_roof_y = SOLAR_ROOF_Y.get(aio_x, pv_t)
    return {
        "solar_label": (solar_x, SOLAR_LABEL_Y),
        "solar_top": (solar_x, solar_roof_y),
        "solar_base": (solar_x, pv_t + pv_h),
        "aio_top": (aio_x, aio_t + int(aio_h * 0.12)),
        "aio_mid": (aio_x, aio_t + aio_h // 2),
        "aio_x": aio_x,
        "aio_edge": aio_edge,
        "aio_connect": aio_connect,
        "window": WINDOW,
        "window_edge": WINDOW_EDGE,
        "hub": HUB,
        "home": (678, 578),
        "grid": GRID,
    }


def flow_paths(anchors: dict[str, tuple[int, int]]) -> dict[str, str]:
    """Fox-style orthogonal paths from locked hub (hub coords must not change)."""
    _, sty = anchors["solar_top"]
    ax = anchors["aio_x"]
    acx, acy = anchors["aio_connect"]
    aty = anchors["aio_top"][1]
    aio_roof_y = SOLAR_ROOF_Y.get(ax, sty)
    wex, wey = anchors["window_edge"]
    hx, hy = anchors["hub"]
    gx, gy = anchors["grid"]
    ground_y = GROUND_Y
    aio_hub = f"M {acx} {acy} L {hx} {hy}"
    hub_aio = f"M {hx} {hy} L {acx} {acy}"
    return {
        "solar-aio": f"M {ax} {aio_roof_y} L {ax} {aty}",
        "grid-hub": f"M {gx} {ground_y} L {hx} {ground_y} L {hx} {hy}",
        "hub-grid": f"M {hx} {hy} L {hx} {ground_y} L {gx} {ground_y}",
        "aio-hub": aio_hub,
        "hub-aio": hub_aio,
        "hub-home": f"M {hx} {hy} L {wex} {wey}",
    }


def place_sprite(theme: str, layer: str) -> None:
    """Prefer bake_flow_home_scenes.ps1 (dwebp decode + matte)."""
    src_name = f"flow_{layer}" if layer == "pv" else "flow_aio_812"
    sprite_path = WWW / f"{src_name}_{theme}_sprite.png"
    src = sprite_path if sprite_path.is_file() else WWW / f"{src_name}_{theme}.png"
    out = WWW / f"flow_{layer}_scene_{theme}.png"
    sprite = remove_black_matte(Image.open(src).convert("RGBA"))
    if layer == "pv":
        from flow_scene_place import DEFAULT_PV, PvPlacement

        canvas = render_pv_layer(sprite, PvPlacement(**DEFAULT_PV))
    else:
        canvas = render_aio_layer(sprite)
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
