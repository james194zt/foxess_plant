#!/usr/bin/env python3
"""Key flow_home mattes and bake matched sky+house into flow_home_bg_scene."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
CANVAS = (1024, 1017)
FLOW_THEMES = ("day_light", "day_dark", "night_light", "night_dark")


def key_edge_black(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    seen = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def is_black(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        return a > 200 and r == 0 and g == 0 and b == 0

    for x in range(w):
        for y in (0, h - 1):
            if is_black(x, y) and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_black(x, y) and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))

    while q:
        x, y = q.popleft()
        px[x, y] = (0, 0, 0, 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and is_black(nx, ny):
                seen[ny][nx] = True
                q.append((nx, ny))

    return im


def needs_edge_key(im: Image.Image) -> bool:
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_opaque_black(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        return a > 200 and r == 0 and g == 0 and b == 0

    for x in range(w):
        if is_opaque_black(x, 0) or is_opaque_black(x, h - 1):
            return True
    for y in range(h):
        if is_opaque_black(0, y) or is_opaque_black(w - 1, y):
            return True
    return False


def load_home_layer(theme: str) -> Image.Image:
    path = WWW / f"flow_home_{theme}.png"
    home = Image.open(path)
    if needs_edge_key(home):
        home = key_edge_black(home)
    else:
        home = home.convert("RGBA")
    if home.size != CANVAS:
        home = home.resize(CANVAS, Image.Resampling.LANCZOS)
    return home


def bake_scene(theme: str, home_layers: dict[str, Image.Image]) -> None:
    """Each theme pairs flow_home_bg_{theme} with flow_home_{theme}."""
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
    canvas.save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes)")


def main() -> None:
    home_layers = {theme: load_home_layer(theme) for theme in FLOW_THEMES}
    for theme in FLOW_THEMES:
        src_path = WWW / f"flow_home_{theme}.png"
        if needs_edge_key(Image.open(src_path)):
            home_layers[theme].save(src_path, optimize=True)
            print(f"keyed {src_path.name} ({src_path.stat().st_size} bytes)")
        else:
            print(f"skip key {src_path.name} (already transparent)")
    for theme in FLOW_THEMES:
        bake_scene(theme, home_layers)


if __name__ == "__main__":
    main()
