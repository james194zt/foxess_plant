#!/usr/bin/env python3
"""Preview Fox flow scene outside Home Assistant (dark canvas + sky + house + pv + aio).

Mirrors the panel layer stack in foxess-plant-panel.js — dark stage (#1a1f26),
flow_home_bg_{theme} sky, flow_home_{theme} house (matte keyed), then pv/aio overlays.

Examples:
  # What is currently in www/ (after bake):
  python tools/preview_flow_scene.py

  # Rebuild PV/AIO from sprites using bake defaults, then composite:
  python tools/preview_flow_scene.py --live

  # Tune PV without touching www/ until it looks right:
  python tools/preview_flow_scene.py --live --pv-scale 0.96 --pv-dy -8
  python tools/preview_flow_scene.py --live --pv-center --pv-dx -12

  # Bake tuned values into www/ and preview:
  python tools/preview_flow_scene.py --live --pv-scale 0.96 --write-www

Output: tools/flow_scene_preview/preview_<theme>.png (open in any image viewer).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image

from flow_scene_place import (
    CANVAS,
    AioPlacement,
    PvPlacement,
    aio_placement_summary,
    composite_scene,
    pv_placement_summary,
    render_aio_layer,
    render_pv_layer,
)
from key_flow_home_sky import build_panel_scene, remove_black_matte

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
OUT_DIR = Path(__file__).resolve().parent / "flow_scene_preview"

OVERLAY_THEMES = ("day_dark", "night_dark")
BG_THEMES = ("day_dark", "night_dark")


def overlay_theme_for_bg(bg_theme: str) -> str:
    return "night_dark" if bg_theme == "night_dark" else "day_dark"


def is_webp(path: Path) -> bool:
    return path.read_bytes()[:4] == b"RIFF"


def load_sprite(layer: str, theme: str) -> Image.Image:
    src_name = f"flow_{layer}" if layer == "pv" else "flow_aio_812"
    src = WWW / f"{src_name}_{theme}.png"
    sprite = WWW / f"{src_name}_{theme}_sprite.png"
    if is_webp(src):
        subprocess.run(["dwebp", str(src), "-o", str(sprite)], check=True)
    elif not sprite.is_file():
        Image.open(src).save(sprite)
    im = Image.open(sprite)
    if im.size == (0, 0):
        raise RuntimeError(f"empty or missing sprite: {sprite}")
    return remove_black_matte(im.convert("RGBA"))


def load_baked_layer(kind: str, theme: str) -> Image.Image:
    if kind == "pv":
        path = WWW / f"flow_pv_scene_{theme}.png"
    elif kind == "aio":
        path = WWW / f"flow_aio_scene_{theme}.png"
    else:
        raise ValueError(kind)
    if not path.is_file():
        raise FileNotFoundError(path)
    return Image.open(path).convert("RGBA")


def composite_panel_scene(bg_theme: str, pv: Image.Image, aio: Image.Image) -> Image.Image:
    return build_panel_scene(bg_theme, pv, aio)


def write_baked_pv(theme: str, layer: Image.Image) -> Path:
    out = WWW / f"flow_pv_scene_{theme}.png"
    layer.save(out, optimize=True)
    return out


def write_baked_aio(theme: str, layer: Image.Image) -> Path:
    out = WWW / f"flow_aio_scene_{theme}.png"
    layer.save(out, optimize=True)
    return out


def preview_theme(
    theme: str,
    bg_theme: str,
    *,
    live: bool,
    placement: PvPlacement,
    aio_placement: AioPlacement,
    write_www: bool,
    also_layers: bool,
) -> Path:
    if live:
        pv_sprite = load_sprite("pv", theme)
        aio_sprite = load_sprite("aio", theme)
        pv = render_pv_layer(pv_sprite, placement)
        aio = render_aio_layer(aio_sprite, aio_placement)
        print(theme, pv_placement_summary(placement, pv_sprite))
        print("      ", aio_placement_summary(aio_placement, aio_sprite))
        if write_www:
            print(f"  wrote {write_baked_pv(theme, pv).relative_to(ROOT)}")
            print(f"  wrote {write_baked_aio(theme, aio).relative_to(ROOT)}")
    else:
        pv = load_baked_layer("pv", theme)
        aio = load_baked_layer("aio", theme)

    composite = composite_panel_scene(bg_theme, pv, aio)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"preview_{bg_theme}.png"
    composite.save(out_path, optimize=True)
    print(f"  composite → {out_path}")

    if also_layers:
        pv_path = OUT_DIR / f"layer_pv_{theme}.png"
        aio_path = OUT_DIR / f"layer_aio_{theme}.png"
        pv.save(pv_path, optimize=True)
        aio.save(aio_path, optimize=True)

    return out_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--theme",
        choices=[*OVERLAY_THEMES, *BG_THEMES, "all", "all-bg"],
        default="day_light",
        help="Overlay theme for pv/aio, or all-bg for every background theme",
    )
    p.add_argument(
        "--bg",
        default=None,
        help="Background scene theme (default: same as --theme)",
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="Build pv/aio layers from sprites (respects --pv-*); default uses baked www PNGs",
    )
    p.add_argument("--write-www", action="store_true", help="With --live, write flow_*_scene_*.png to www/")
    p.add_argument("--layers", action="store_true", help="Also write separate layer_pv_* and layer_aio_* PNGs")
    p.add_argument("--pv-scale", type=float, default=None, metavar="F", help="Uniform scale vs box-fit (e.g. 0.98)")
    p.add_argument("--pv-dx", type=int, default=None, help="Extra paste offset X (px); default from flow_scene_place")
    p.add_argument("--pv-dy", type=int, default=None, help="Extra paste offset Y (px); default from flow_scene_place")
    p.add_argument("--pv-center", action="store_true", help="Center in box instead of box top-left origin")
    p.add_argument("--aio-scale", type=float, default=None, metavar="F", help="AIO uniform scale inset (default bake value)")
    p.add_argument("--aio-dx", type=int, default=None, help="AIO paste offset X (px)")
    p.add_argument("--aio-dy", type=int, default=None, help="AIO paste offset Y (px)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    from flow_scene_place import DEFAULT_AIO, DEFAULT_PV

    placement = PvPlacement(
        scale_inset=args.pv_scale if args.pv_scale is not None else DEFAULT_PV["scale_inset"],
        at_box_origin=not args.pv_center,
        dx=args.pv_dx if args.pv_dx is not None else DEFAULT_PV["dx"],
        dy=args.pv_dy if args.pv_dy is not None else DEFAULT_PV["dy"],
    )
    aio_placement = AioPlacement(
        scale_inset=args.aio_scale if args.aio_scale is not None else DEFAULT_AIO["scale_inset"],
        dx=args.aio_dx if args.aio_dx is not None else DEFAULT_AIO["dx"],
        dy=args.aio_dy if args.aio_dy is not None else DEFAULT_AIO["dy"],
    )

    if args.theme == "all":
        themes = list(OVERLAY_THEMES)
    elif args.theme == "all-bg":
        themes = list(BG_THEMES)
    elif args.theme in BG_THEMES:
        themes = [args.theme]
    else:
        themes = [args.theme]
    print(f"Canvas {CANVAS[0]}×{CANVAS[1]} — mode {'live' if args.live else 'baked www'}")

    paths: list[Path] = []
    for theme in themes:
        if theme in BG_THEMES:
            bg_theme = theme
            overlay_theme = overlay_theme_for_bg(bg_theme)
        else:
            overlay_theme = theme
            bg_theme = args.bg or theme
        if bg_theme not in BG_THEMES:
            print(f"skip {theme}: unknown bg theme {bg_theme}", file=sys.stderr)
            continue
        try:
            paths.append(
                preview_theme(
                    overlay_theme,
                    bg_theme,
                    live=args.live,
                    placement=placement,
                    aio_placement=aio_placement,
                    write_www=args.write_www,
                    also_layers=args.layers,
                )
            )
        except FileNotFoundError as err:
            print(f"skip {theme}: {err}", file=sys.stderr)

    if not paths:
        return 1
    print("\nOpen in Explorer:")
    for path in paths:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
