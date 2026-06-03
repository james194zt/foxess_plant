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


def strip_ground_plane(
    im: Image.Image,
    *,
    min_lum: int = 48,
    max_lum: int = 205,
    max_sat: int = 48,
    band_px: int = 88,
) -> Image.Image:
    """Remove only the grey ground apron under the house (not white walls)."""
    im = im.convert("RGBA")
    alpha = im.split()[3]
    bbox = alpha.getbbox()
    if not bbox:
        return im
    _, _y0, _, y1 = bbox
    ground_start = max(0, y1 - band_px)
    px = im.load()
    w, h = im.size
    for y in range(ground_start, h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0:
                continue
            na = max(r, g, b)
            sat = max(r, g, b) - min(r, g, b)
            if sat <= max_sat and min_lum <= na <= max_lum:
                px[x, y] = (0, 0, 0, 0)
    return im


def feather_home_ground(im: Image.Image, band_px: int = 72, power: float = 1.45) -> Image.Image:
    """Extra soft fade at house base (grey apron → dark stage)."""
    im = im.convert("RGBA")
    alpha = im.split()[3]
    bbox = alpha.getbbox()
    if not bbox:
        return im
    _, _y0, _, y1 = bbox
    ground_start = max(0, y1 - band_px)
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
    return feather_home_ground(strip_ground_plane(remove_black_matte_only(home)))


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def paint_css_sky(canvas: Image.Image, bg_theme: str) -> None:
    """Match panel CSS sky gradients (no sky PNG — avoids ground plate)."""
    w, h = canvas.size
    px = canvas.load()
    if bg_theme == "day_dark":
        stops = [(0.0, (42, 74, 98)), (0.28, (61, 90, 114)), (0.50, (26, 31, 38))]
    else:
        stops = [(0.0, (61, 127, 184)), (0.20, (111, 163, 204)), (0.36, (168, 196, 220)), (0.52, (26, 31, 38))]
    for y in range(h):
        t = y / max(1, h - 1)
        if t >= stops[-1][0]:
            r, g, b = stops[-1][1]
        else:
            for i in range(len(stops) - 1):
                t0, c0 = stops[i]
                t1, c1 = stops[i + 1]
                if t0 <= t <= t1:
                    f = (t - t0) / (t1 - t0) if t1 > t0 else 0
                    r = _lerp(c0[0], c1[0], f)
                    g = _lerp(c0[1], c1[1], f)
                    b = _lerp(c0[2], c1[2], f)
                    break
        for x in range(w):
            px[x, y] = (r, g, b, 255)


def paste_night_sky_top(canvas: Image.Image, bg_theme: str, top_frac: float = 0.44) -> None:
    """Only the upper sky from PNG; lower frame stays dark canvas (Fox-style)."""
    src = WWW / f"flow_home_bg_{bg_theme}.png"
    bg = remove_black_matte_only(Image.open(src).convert("RGBA"))
    scale = max(CANVAS[0] / bg.width, CANVAS[1] / bg.height)
    nw, nh = int(bg.width * scale), int(bg.height * scale)
    bg = bg.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (CANVAS[0] - nw) // 2
    y = CANVAS[1] - nh
    crop_h = max(1, int(nh * top_frac))
    top = bg.crop((0, 0, nw, crop_h))
    canvas.paste(top, (x, y), top)


def apply_ground_vignette(canvas: Image.Image) -> None:
    """Soft dark fade at base — window spill blends into stage."""
    w, h = canvas.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    bg = CANVAS_BG_RGBA
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.58:
            continue
        fade = ((t - 0.58) / 0.42) ** 1.35
        alpha = int(255 * min(1.0, fade * 0.72))
        for x in range(w):
            px[x, y] = (*bg[:3], alpha)
    canvas.alpha_composite(overlay)


def build_panel_scene(bg_theme: str, home: Image.Image, pv: Image.Image, aio: Image.Image) -> Image.Image:
    """Same stack as foxess-plant-panel.js after v0.8.146."""
    out = Image.new("RGBA", CANVAS, CANVAS_BG_RGBA)
    if bg_theme.startswith("day_"):
        paint_css_sky(out, bg_theme)
    else:
        paste_night_sky_top(out, bg_theme)
    out.alpha_composite(home.convert("RGBA"))
    apply_ground_vignette(out)
    out.alpha_composite(pv.convert("RGBA"))
    out.alpha_composite(aio.convert("RGBA"))
    return out


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
