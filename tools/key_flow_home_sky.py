#!/usr/bin/env python3
"""Remove black mattes and bake matched sky+house flow_home_bg_scene assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
CANVAS = (1024, 1017)
FLOW_THEMES = ("day_light", "day_dark", "night_light", "night_dark")
MATTE_LUM = 28
# Fox app flow stage (sync FLOW_SCENE_CANVAS_BG in foxess-plant-panel.js)
CANVAS_BG_RGBA = (26, 31, 38, 255)


def luminance_matte(im: Image.Image, black_cut: int = MATTE_LUM) -> Image.Image:
    """Fox-style matte: max(R,G,B) becomes alpha so grey ground dissolves on dark canvas."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            na = max(r, g, b)
            if na <= black_cut:
                px[x, y] = (0, 0, 0, 0)
                continue
            nr = min(255, int(round(r * 255 / na)))
            ng = min(255, int(round(g * 255 / na)))
            nb = min(255, int(round(b * 255 / na)))
            px[x, y] = (nr, ng, nb, na)
    return im


def strip_grey_ground_apron(
    im: Image.Image,
    *,
    grey_lo: int = 42,
    grey_hi: int = 218,
    max_sat: int = 38,
    band_frac: float = 0.34,
) -> Image.Image:
    """Remove opaque grey/white ground plane under house (Fox fades into dark stage)."""
    im = im.convert("RGBA")
    alpha = im.split()[3]
    bbox = alpha.getbbox()
    if not bbox:
        return im
    _, y0, _, y1 = bbox
    ground_start = int(y1 - (y1 - y0) * band_frac)
    px = im.load()
    w, h = im.size
    for y in range(ground_start, h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0:
                continue
            na = max(r, g, b)
            sat = max(r, g, b) - min(r, g, b)
            if sat <= max_sat and grey_lo <= na <= grey_hi:
                px[x, y] = (0, 0, 0, 0)
    return im


def dissolve_sky_horizon(im: Image.Image, start_frac: float = 0.54, power: float = 1.22) -> Image.Image:
    """Fade sky art into dark stage from mid-frame down (removes opaque ground plate)."""
    im = im.convert("RGBA")
    w, h = im.size
    y0 = int(h * start_frac)
    px = im.load()
    for y in range(y0, h):
        t = (y - y0) / max(1, h - y0 - 1)
        mul = max(0.0, 1.0 - (t**power))
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0:
                continue
            na = max(r, g, b)
            sat = max(r, g, b) - min(r, g, b)
            if na <= MATTE_LUM:
                px[x, y] = (0, 0, 0, 0)
                continue
            if sat <= 44 and na <= 210:
                key_a = int(na * mul)
                if key_a <= MATTE_LUM:
                    px[x, y] = (0, 0, 0, 0)
                    continue
                nr = min(255, int(round(r * 255 / na)))
                ng = min(255, int(round(g * 255 / na)))
                nb = min(255, int(round(b * 255 / na)))
                px[x, y] = (nr, ng, nb, key_a)
            else:
                new_a = int(a * mul)
                if new_a <= MATTE_LUM:
                    px[x, y] = (0, 0, 0, 0)
                else:
                    px[x, y] = (r, g, b, new_a)
    return im


def feather_home_ground(im: Image.Image, band_frac: float = 0.3, power: float = 1.35) -> Image.Image:
    """Extra soft fade at house base (grey apron → dark stage)."""
    im = im.convert("RGBA")
    alpha = im.split()[3]
    bbox = alpha.getbbox()
    if not bbox:
        return im
    _, y0, _, y1 = bbox
    ground_start = int(y1 - (y1 - y0) * band_frac)
    px = im.load()
    w, h = im.size
    for y in range(ground_start, h):
        t = (y - ground_start) / max(1, h - ground_start - 1)
        mul = 1.0 - (t**power)
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0:
                continue
            na = int(a * mul)
            if na <= 0:
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = (r, g, b, na)
    return im


def remove_black_matte_only(im: Image.Image, lum: int = MATTE_LUM) -> Image.Image:
    """Key only near-black mattes; leave house walls opaque."""
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
                px[x, y] = (r, g, b, na)
    return im


def remove_black_matte(im: Image.Image, lum: int = MATTE_LUM) -> Image.Image:
    """Sprites (pv/aio): full luminance matte."""
    return luminance_matte(im, black_cut=lum)


def process_home_layer(home: Image.Image) -> Image.Image:
    return feather_home_ground(strip_grey_ground_apron(remove_black_matte_only(home)))


def load_sky_layer(bg_theme: str) -> Image.Image:
    """Sky on dark Fox canvas (use rekeyed flow_home_bg_* assets)."""
    src = WWW / f"flow_home_bg_{bg_theme}.png"
    bg = Image.open(src).convert("RGBA")
    scale = max(CANVAS[0] / bg.width, CANVAS[1] / bg.height)
    nw, nh = int(bg.width * scale), int(bg.height * scale)
    bg = bg.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, CANVAS_BG_RGBA)
    x = (CANVAS[0] - nw) // 2
    y = CANVAS[1] - nh
    canvas.paste(bg, (x, y), bg)
    return canvas


def load_home_layer(theme: str) -> Image.Image:
    path = WWW / f"flow_home_{theme}.png"
    home = Image.open(path).convert("RGBA")
    if home.size != CANVAS:
        home = home.resize(CANVAS, Image.Resampling.LANCZOS)
    return home


def bake_scene(theme: str, home_layers: dict[str, Image.Image]) -> None:
    src = WWW / f"flow_home_bg_{theme}.png"
    out = WWW / f"flow_home_bg_scene_{theme}.png"
    bg = Image.open(src).convert("RGBA")
    scale = max(CANVAS[0] / bg.width, CANVAS[1] / bg.height)
    nw, nh = int(bg.width * scale), int(bg.height * scale)
    bg = bg.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, CANVAS_BG_RGBA)
    x = (CANVAS[0] - nw) // 2
    y = CANVAS[1] - nh
    canvas.paste(bg, (x, y), bg)
    canvas = Image.alpha_composite(canvas, home_layers[theme])
    canvas.save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes)")


def main() -> None:
    home_layers = {theme: load_home_layer(theme) for theme in FLOW_THEMES}
    for theme in FLOW_THEMES:
        bake_scene(theme, home_layers)


if __name__ == "__main__":
    main()
