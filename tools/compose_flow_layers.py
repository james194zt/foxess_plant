#!/usr/bin/env python3
"""Bake flow_pv and flow_aio sprites onto 1024×1017 transparent canvases (Fox scene coords)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from key_flow_home_sky import remove_black_matte

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
CANVAS = (1024, 1017)

# Fractions of 1024×1017 — tune here, then re-run: python tools/compose_flow_layers.py
BOXES = {
    "aio": {"left": 0.312, "top": 0.622, "width": 0.136, "height": 0.222},
}
# PV uses perspective quad in tools/bake_flow_home_scenes.ps1 (not axis-aligned box).
PV_ROOF_QUAD = (
    (422, 410),
    (706, 368),
    (438, 558),
)

# Scene anchors (viewBox 0 0 1024 1017)
# LOCKED (v0.8.47): HUB was hand-tuned on the side/front wall corner — do NOT change
# coordinates unless the user explicitly asks. Sync FOX_FLOW_HUB / FOX_FLOW_PATHS in panel JS.
HUB = (536, 726)
# Side-face x at hub row; y derived parallel to hub-home / house base (28px rise per 100px run)
AIO_FACE_X = 405
WALL_3D_RISE_RUN = (726 - 698) / (636 - 536)  # hub-home slope — parallel perspective lines
AIO_CONNECT = (AIO_FACE_X, round(HUB[1] - (HUB[0] - AIO_FACE_X) * WALL_3D_RISE_RUN))
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


def _pv_quad_metrics() -> tuple[int, int, int, int]:
    (tlx, tly), (trx, try_), (blx, bly) = PV_ROOF_QUAD
    brx = blx + trx - tlx
    bry = bly + try_ - tly
    solar_x = (tlx + trx + blx + brx) // 4
    pv_top = min(tly, try_)
    pv_bottom = max(bly, bry)
    return solar_x, pv_top, pv_bottom, try_


def derive_anchors() -> dict[str, tuple[int, int]]:
    solar_x, pv_top, pv_bottom, _pv_try = _pv_quad_metrics()
    aio_l, aio_t, aio_w, aio_h = box_pixels(BOXES["aio"])
    aio_x = aio_l + aio_w // 2
    aio_edge = aio_l + aio_w  # right edge of AIO placement box
    aio_connect = AIO_CONNECT  # tap visible AIO face (pixel-tuned on flow_aio_scene)
    solar_roof_y = SOLAR_ROOF_Y.get(solar_x, pv_top)
    aio_roof_y = SOLAR_ROOF_Y.get(aio_x, pv_top)
    return {
        "solar_label": (solar_x, SOLAR_LABEL_Y),
        "solar_top": (solar_x, solar_roof_y),
        "solar_base": (solar_x, pv_bottom),
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
    """Bake AIO only; run bake_flow_home_scenes.ps1 for PV perspective placement."""
    if layer != "aio":
        print(f"skip {layer}: use bake_flow_home_scenes.ps1")
        return
    src = WWW / f"flow_aio_812_{theme}.png"
    out = WWW / f"flow_{layer}_scene_{theme}.png"
    sprite = remove_black_matte(Image.open(src).convert("RGBA"))
    left, top, bw, bh = box_pixels(BOXES[layer])
    fitted = sprite.resize((bw, bh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.paste(fitted, (left, top), fitted)
    canvas.save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes)")


def main() -> None:
    for theme in ("day_light", "night_dark"):
        place_sprite(theme, "aio")
    a = derive_anchors()
    paths = flow_paths(a)
    print("anchors", a)
    print("FOX_FLOW_HUB", f"{{ x: {a['hub'][0]}, y: {a['hub'][1]} }};")
    print("FOX_FLOW_PATHS", paths)


if __name__ == "__main__":
    main()
