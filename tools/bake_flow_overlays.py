#!/usr/bin/env python3
"""Decode WEBP sprites (dwebp) and bake flow_pv / flow_aio scene overlays."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from key_flow_home_sky import remove_black_matte

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
CANVAS = (1024, 1017)

# PV: uniform scale keeps baked perspective; inset + offset fit the roof face (no overhang).
BOXES = {
    "pv": {"left": 0.388, "top": 0.342, "width": 0.448, "height": 0.242},
    "aio": {"left": 0.312, "top": 0.622, "width": 0.136, "height": 0.222},
}
# Box-fit at Fox paste origin (left/top); slight inset trims gable/ridge overhang.
PV_SCALE_INSET = 0.98
PV_PASTE_AT_BOX_ORIGIN = True


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


def box_pixels(box: dict) -> tuple[int, int, int, int]:
    w, h = CANVAS
    return (
        int(box["left"] * w),
        int(box["top"] * h),
        int(box["width"] * w),
        int(box["height"] * h),
    )


def bake_pv(theme: str) -> None:
    left, top, bw, bh = box_pixels(BOXES["pv"])
    sprite = load_sprite("pv", theme)
    sw, sh = sprite.size
    scale = min(bw / sw, bh / sh) * PV_SCALE_INSET
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    scaled = sprite.resize((nw, nh), Image.Resampling.LANCZOS)
    if PV_PASTE_AT_BOX_ORIGIN:
        px, py = left, top
    else:
        px = left + (bw - nw) // 2
        py = top + (bh - nh) // 2
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.paste(scaled, (px, py), scaled)
    out = WWW / f"flow_pv_scene_{theme}.png"
    canvas.save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes) {nw}x{nh} @ ({px},{py})")


def bake_aio(theme: str) -> None:
    left, top, bw, bh = box_pixels(BOXES["aio"])
    sprite = load_sprite("aio", theme)
    fitted = sprite.resize((bw, bh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.paste(fitted, (left, top), fitted)
    out = WWW / f"flow_aio_scene_{theme}.png"
    canvas.save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes)")


def main() -> None:
    for theme in ("day_light", "night_dark"):
        bake_pv(theme)
        bake_aio(theme)


if __name__ == "__main__":
    main()
