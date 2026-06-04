#!/usr/bin/env python3
"""Generate PV roof placement variants for visual pick (day_light composite)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from flow_scene_place import AioPlacement, PvPlacement, render_aio_layer, render_pv_layer
from key_flow_home_sky import build_panel_scene
from preview_flow_scene import load_sprite

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "flow_scene_preview"
THEME = "day_light"
BG_THEME = "day_light"

# (label, PvPlacement kwargs)
VARIANTS: list[tuple[str, dict]] = [
    ("a_current", {"scale_inset": 1.04, "at_box_origin": True, "anchor": "tl", "dx": 0, "dy": 18}),
    ("b_tl_up_right", {"scale_inset": 1.09, "at_box_origin": True, "anchor": "tl", "dx": 12, "dy": 4}),
    ("c_tl_more", {"scale_inset": 1.11, "at_box_origin": True, "anchor": "tl", "dx": 18, "dy": 0}),
    ("d_tl_tight", {"scale_inset": 1.10, "at_box_origin": True, "anchor": "tl", "dx": 14, "dy": 2}),
    ("e_bl_anchor", {"scale_inset": 1.08, "at_box_origin": True, "anchor": "bl", "dx": -4, "dy": -6}),
    ("f_br_anchor", {"scale_inset": 1.08, "at_box_origin": True, "anchor": "br", "dx": 6, "dy": -8}),
    ("g_bl_fill", {"scale_inset": 1.10, "at_box_origin": True, "anchor": "bl", "dx": 0, "dy": -4}),
    ("h_center", {"scale_inset": 1.10, "at_box_origin": False, "anchor": "center", "dx": 4, "dy": -6}),
    ("h_center_dy6", {"scale_inset": 1.10, "at_box_origin": False, "anchor": "center", "dx": 4, "dy": 6}),
    ("h_center_dy10", {"scale_inset": 1.10, "at_box_origin": False, "anchor": "center", "dx": 4, "dy": 10}),
    ("h_center_dy14", {"scale_inset": 1.10, "at_box_origin": False, "anchor": "center", "dx": 4, "dy": 14}),
    ("h_center_dy6_back2", {"scale_inset": 1.10, "at_box_origin": False, "anchor": "center", "dx": 6, "dy": 6}),
    ("h_center_dy6_back3", {"scale_inset": 1.10, "at_box_origin": False, "anchor": "center", "dx": 7, "dy": 6}),
    ("h_center_dy6_back4", {"scale_inset": 1.10, "at_box_origin": False, "anchor": "center", "dx": 8, "dy": 6}),
]


def _label(im: Image.Image, text: str) -> Image.Image:
    out = im.copy()
    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    draw.rectangle((8, 8, 8 + len(text) * 11, 40), fill=(0, 0, 0, 180))
    draw.text((12, 10), text, fill=(255, 255, 255, 255), font=font)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pv_sprite = load_sprite("pv", THEME)
    aio_sprite = load_sprite("aio", THEME)
    aio = render_aio_layer(aio_sprite, AioPlacement())

    thumbs: list[Image.Image] = []
    paths: list[Path] = []

    for label, kwargs in VARIANTS:
        placement = PvPlacement(**kwargs)
        pv = render_pv_layer(pv_sprite, placement)
        scene = build_panel_scene(BG_THEME, pv, aio)
        tagged = _label(scene, label)
        out = OUT / f"pv_roof_{label}.png"
        tagged.save(out, optimize=True)
        paths.append(out)
        thumbs.append(tagged.resize((512, 508), Image.Resampling.LANCZOS))
        print(label, kwargs)

    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 512, rows * 508), (26, 31, 38))
    for i, thumb in enumerate(thumbs):
        x = (i % cols) * 512
        y = (i // cols) * 508
        sheet.paste(thumb, (x, y))
    sheet_path = OUT / "pv_roof_variants_sheet.png"
    sheet.save(sheet_path, optimize=True)
    print(f"\nWrote {len(paths)} previews + {sheet_path}")
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
