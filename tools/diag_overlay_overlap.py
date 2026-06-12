#!/usr/bin/env python3
"""Compare house backdrop vs PV/AIO overlay overlap."""
from pathlib import Path

from PIL import Image, ImageDraw

WWW = Path(__file__).resolve().parents[1] / "custom_components/foxess_plant/www"
OUT = Path(__file__).resolve().parent / "flow_scene_preview"
THEME = "day_dark"
CANVAS = (1024, 1017)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bg_scene = Image.open(WWW / f"flow_home_bg_scene_{THEME}.png").convert("RGBA")
    pv_scene = Image.open(WWW / f"flow_pv_scene_{THEME}.png").convert("RGBA")
    aio_scene = Image.open(WWW / f"flow_aio_scene_{THEME}.png").convert("RGBA")
    pv_sprite = Image.open(WWW / f"flow_pv_{THEME}_sprite.png").convert("RGBA")
    aio_sprite = Image.open(WWW / f"flow_aio_812_{THEME}_sprite.png").convert("RGBA")

    # Where overlays have opaque pixels
    for name, im in [("pv_scene", pv_scene), ("aio_scene", aio_scene), ("pv_sprite", pv_sprite), ("aio_sprite", aio_sprite)]:
        bb = im.getchannel("A").getbbox()
        print(f"{name} bbox={bb} size={im.size}")

    # Red tint overlay regions on backdrop
    def tint_overlay(base: Image.Image, overlay: Image.Image, color: tuple) -> Image.Image:
        out = base.copy()
        px = overlay.load()
        opx = out.load()
        w, h = overlay.size
        for y in range(h):
            for x in range(w):
                if px[x, y][3] > 30:
                    r, g, b, a = opx[x, y]
                    opx[x, y] = (
                        min(255, (r + color[0]) // 2),
                        min(255, (g + color[1]) // 2),
                        min(255, (b + color[2]) // 2),
                        a,
                    )
        return out

    tint_pv = tint_overlay(bg_scene, pv_scene, (255, 0, 0))
    tint_both = tint_overlay(tint_pv, aio_scene, (0, 255, 0))
    tint_both.save(OUT / f"overlap_{THEME}.png")

    pv_sprite.save(OUT / f"sprite_pv_{THEME}.png")
    aio_sprite.save(OUT / f"sprite_aio_{THEME}.png")
    print(f"wrote {OUT}/overlap_{THEME}.png")


if __name__ == "__main__":
    main()
