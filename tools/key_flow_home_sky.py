#!/usr/bin/env python3
"""Make flow_home sky/letterbox pure-black pixels transparent; bake bg to scene canvas."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
CANVAS = (1024, 1017)
FLOW_BG_THEMES = ("day_light", "day_dark", "night_light", "night_dark")
FLOW_HOME_THEMES = ("day_light", "night_dark")


def key_edge_black(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    seen = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def is_black(x: int, y: int) -> bool:
        r, g, b, _a = px[x, y]
        return r == 0 and g == 0 and b == 0

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


def bake_bg(theme: str) -> None:
    src = WWW / f"flow_home_bg_{theme}.png"
    out = WWW / f"flow_home_bg_scene_{theme}.png"
    bg = Image.open(src).convert("RGBA")
    scale = max(CANVAS[0] / bg.width, CANVAS[1] / bg.height)
    nw, nh = int(bg.width * scale), int(bg.height * scale)
    bg = bg.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 255))
    x = (CANVAS[0] - nw) // 2
    canvas.paste(bg, (x, 0), bg)
    canvas.save(out, optimize=True)
    print(f"wrote {out.name} ({out.stat().st_size} bytes)")


def main() -> None:
    for theme in FLOW_HOME_THEMES:
        home = WWW / f"flow_home_{theme}.png"
        keyed = key_edge_black(Image.open(home))
        keyed.save(home, optimize=True)
        print(f"keyed {home.name} ({home.stat().st_size} bytes)")
    for theme in FLOW_BG_THEMES:
        bake_bg(theme)


if __name__ == "__main__":
    main()
