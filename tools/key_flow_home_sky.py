#!/usr/bin/env python3
"""Remove black mattes and bake matched sky+house flow_home_bg_scene assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
CANVAS = (1024, 1017)
FLOW_THEMES = ("day_light", "day_dark", "night_light", "night_dark")
MATTE_LUM = 48


def remove_black_matte(im: Image.Image, lum: int = MATTE_LUM) -> Image.Image:
    """Un-premultiply anti-aliased edges exported on a black background."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            na = max(r, g, b)
            if na > lum:
                continue
            if na == 0:
                px[x, y] = (0, 0, 0, 0)
            else:
                scale = 255.0 / na
                px[x, y] = (
                    min(255, int(r * scale)),
                    min(255, int(g * scale)),
                    min(255, int(b * scale)),
                    na,
                )
    return im


def load_home_layer(theme: str) -> Image.Image:
    path = WWW / f"flow_home_{theme}.png"
    home = Image.open(path).convert("RGBA")
    if home.size != CANVAS:
        home = home.resize(CANVAS, Image.Resampling.LANCZOS)
    return remove_black_matte(home)


def bake_scene(theme: str, home_layers: dict[str, Image.Image]) -> None:
    src = WWW / f"flow_home_bg_{theme}.png"
    out = WWW / f"flow_home_bg_scene_{theme}.png"
    bg = Image.open(src).convert("RGBA")
    scale = max(CANVAS[0] / bg.width, CANVAS[1] / bg.height)
    nw, nh = int(bg.width * scale), int(bg.height * scale)
    bg = bg.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 255))
    x = (CANVAS[0] - nw) // 2
    y = CANVAS[1] - nh
    canvas.paste(bg, (x, y), bg)
    canvas = Image.alpha_composite(canvas, home_layers[theme])
    canvas.convert("RGB").save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes)")


def main() -> None:
    home_layers = {theme: load_home_layer(theme) for theme in FLOW_THEMES}
    for theme in FLOW_THEMES:
        bake_scene(theme, home_layers)


if __name__ == "__main__":
    main()
