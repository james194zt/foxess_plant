#!/usr/bin/env python3
"""Decode WEBP sprites (dwebp) and bake flow_pv / flow_aio scene overlays."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from flow_scene_place import (
    DEFAULT_AIO,
    DEFAULT_PV,
    AioPlacement,
    PvPlacement,
    render_aio_layer,
    render_pv_layer,
)
from key_flow_home_sky import remove_black_matte

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"

# Re-export for tools that import bake constants.
PV_SCALE_INSET = DEFAULT_PV["scale_inset"]
PV_PASTE_AT_BOX_ORIGIN = DEFAULT_PV["at_box_origin"]
PV_PASTE_DX = DEFAULT_PV["dx"]
PV_PASTE_DY = DEFAULT_PV["dy"]

DEFAULT_PV_PLACEMENT = PvPlacement(**DEFAULT_PV)
DEFAULT_AIO_PLACEMENT = AioPlacement(**DEFAULT_AIO)


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
    if im.size != (0, 0):
        return remove_black_matte(im.convert("RGBA"))
    raise RuntimeError(f"empty or missing sprite: {sprite}")


def bake_pv(theme: str, placement: PvPlacement | None = None) -> None:
    placement = placement or DEFAULT_PV_PLACEMENT
    sprite = load_sprite("pv", theme)
    canvas = render_pv_layer(sprite, placement)
    out = WWW / f"flow_pv_scene_{theme}.png"
    canvas.save(out, optimize=True)
    bbox = canvas.getbbox()
    print(f"wrote {out.name} ({out.stat().st_size} bytes) bbox={bbox}")


def bake_aio(theme: str, placement: AioPlacement | None = None) -> None:
    placement = placement or DEFAULT_AIO_PLACEMENT
    sprite = load_sprite("aio", theme)
    canvas = render_aio_layer(sprite, placement)
    out = WWW / f"flow_aio_scene_{theme}.png"
    canvas.save(out, optimize=True)
    bbox = canvas.getbbox()
    print(f"wrote {out.name} ({out.stat().st_size} bytes) bbox={bbox}")


def main() -> None:
    for theme in ("day_dark", "night_dark"):
        bake_pv(theme)
        bake_aio(theme)


if __name__ == "__main__":
    main()
