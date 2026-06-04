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
CANVAS_BG_RGBA = (10, 12, 15, 255)


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


def detect_ground_fog_start(im: Image.Image) -> int:
    """Row where centre column leaves solid white wall into grey render fog."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    cx = w // 2
    for y in range(int(h * 0.52), h):
        r, g, b, a = px[cx, y]
        if a < 64:
            continue
        na = max(r, g, b)
        sat = max(r, g, b) - min(r, g, b)
        if sat <= 10 and na < 243:
            return y
    return int(h * 0.8)


def dissolve_ground_fog(im: Image.Image, y0: int | None = None) -> Image.Image:
    """Fade render fog/plate below house feet (Fox: dark stage, no patio slab)."""
    im = im.convert("RGBA")
    w, h = im.size
    if y0 is None:
        y0 = min(detect_ground_fog_start(im), int(h * 0.802))
    y0 = int(h * 0.758)
    fade_end = min(h - 1, y0 + 200)
    px = im.load()
    for y in range(y0, h):
        if y <= fade_end:
            crush = ((y - y0) / max(1, fade_end - y0)) ** 0.88
        else:
            crush = 1.0
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0:
                continue
            na = max(r, g, b)
            sat = max(r, g, b) - min(r, g, b)
            if sat > 16 or na < 72:
                continue
            fade = int(a * (1.0 - crush))
            if fade <= 4:
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = (r, g, b, fade)
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


def strip_aio_reflection(sprite: Image.Image) -> Image.Image:
    """Drop floor reflection below the cabinet (Fox art includes it; duplicates on dark stage)."""
    from flow_scene_place import AIO_OPAQUE_FRAC

    im = sprite.convert("RGBA")
    _, _, _, oy1 = AIO_OPAQUE_FRAC
    sh = im.height
    cut = min(sh, int(sh * oy1) + 2)
    px = im.load()
    w = im.width
    for y in range(cut, sh):
        for x in range(w):
            px[x, y] = (0, 0, 0, 0)
    return im


def process_pv_sprite(sprite: Image.Image) -> Image.Image:
    """PV on roof: key black only so panel edges stay crisp (no grey halo)."""
    return remove_black_matte_only(sprite)


def process_aio_sprite(sprite: Image.Image) -> Image.Image:
    """Wall AIO: cabinet only — no ground reflection under the unit."""
    return remove_black_matte_only(strip_aio_reflection(sprite))


def process_home_layer(home: Image.Image) -> Image.Image:
    home = remove_black_matte_only(home)
    home = luminance_matte(home)
    return dissolve_ground_fog(home)


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def paint_css_sky(canvas: Image.Image, bg_theme: str) -> None:
    """Match panel CSS sky gradients (no sky PNG — avoids ground plate)."""
    w, h = canvas.size
    px = canvas.load()
    if bg_theme == "day_dark":
        stops = [(0.0, (42, 74, 98)), (0.22, (58, 88, 112)), (0.36, (26, 31, 38))]
    else:
        stops = [(0.0, (55, 118, 175)), (0.18, (98, 150, 188)), (0.34, (26, 31, 38))]
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


def paste_bg_layer(canvas: Image.Image, bg_theme: str) -> None:
    """Scale flow_home_bg to canvas bottom (matches panel object-fit: contain bottom)."""
    src = Image.open(WWW / f"flow_home_bg_{bg_theme}.png").convert("RGBA")
    scale = max(CANVAS[0] / src.width, CANVAS[1] / src.height)
    nw, nh = int(src.width * scale), int(src.height * scale)
    bg = src.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (CANVAS[0] - nw) // 2
    y = CANVAS[1] - nh
    canvas.paste(bg, (x, y), bg)


def build_panel_scene(bg_theme: str, pv: Image.Image, aio: Image.Image) -> Image.Image:
    """Baked backdrop (1024×1017) + existing tuned pv/aio scene layers."""
    out = Image.open(WWW / f"flow_home_bg_scene_{bg_theme}.png").convert("RGBA")
    if out.size != CANVAS:
        out = out.resize(CANVAS, Image.Resampling.LANCZOS)
    out.alpha_composite(pv.convert("RGBA"))
    out.alpha_composite(aio.convert("RGBA"))
    return out


def canvas_bg_for_theme(theme: str) -> tuple[int, int, int, int]:
    """Fox _light art targets a white stage; _dark art targets black (matches HA UI theme)."""
    if theme.endswith("_light"):
        return (255, 255, 255, 255)
    return (0, 0, 0, 255)


def bake_bg_scene(theme: str, home: Image.Image | None = None) -> None:
    """Bake flow_home_bg + black-matte house → flow_home_bg_scene (matches bake_flow_home_scenes.ps1)."""
    src = Image.open(WWW / f"flow_home_bg_{theme}.png").convert("RGBA")
    if home is None:
        home = Image.open(WWW / f"flow_home_{theme}.png").convert("RGBA")
        if home.size != CANVAS:
            home = home.resize(CANVAS, Image.Resampling.LANCZOS)
        home = remove_black_matte_only(home)
    scale = max(CANVAS[0] / src.width, CANVAS[1] / src.height)
    nw, nh = int(src.width * scale), int(src.height * scale)
    bg = src.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (CANVAS[0] - nw) // 2
    y = CANVAS[1] - nh
    canvas = Image.new("RGBA", CANVAS, canvas_bg_for_theme(theme))
    canvas.paste(bg, (x, y), bg)
    canvas.alpha_composite(home.convert("RGBA"))
    out = WWW / f"flow_home_bg_scene_{theme}.png"
    canvas.convert("RGB").save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes)")


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
