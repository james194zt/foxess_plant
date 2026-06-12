#!/usr/bin/env python3
"""Composite Fox APK webps the Android way (bg background + full-bleed home)."""
from pathlib import Path

from PIL import Image

APK = Path("/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/res/mipmap-nodpi-v4")
OUT = Path(__file__).resolve().parent / "flow_scene_preview"
CANVAS = (1024, 1017)
THEME = "day_light"


def load(name: str) -> Image.Image:
    return Image.open(APK / name).convert("RGBA")


def android_bg(canvas: Image.Image, bg: Image.Image) -> None:
    """ConstraintLayout background: scale to cover, center."""
    cw, ch = canvas.size
    scale = max(cw / bg.width, ch / bg.height)
    nw, nh = int(bg.width * scale), int(bg.height * scale)
    bg = bg.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (cw - nw) // 2
    y = (ch - nh) // 2
    canvas.paste(bg, (x, y), bg)


def android_imageview(canvas: Image.Image, img: Image.Image) -> None:
    """match_parent ImageView default FIT_CENTER: fit inside, center."""
    cw, ch = canvas.size
    scale = min(cw / img.width, ch / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (cw - nw) // 2
    y = (ch - nh) // 2
    canvas.alpha_composite(img, (x, y))


def css_contain_bottom(canvas: Image.Image, img: Image.Image) -> None:
    """HA panel: object-fit contain, object-position center bottom."""
    cw, ch = canvas.size
    scale = min(cw / img.width, ch / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (cw - nw) // 2
    y = ch - nh
    canvas.alpha_composite(img, (x, y))


def main() -> None:
    bg = load(f"flow_home_bg_{THEME}.webp")
    home = load(f"flow_home_{THEME}.webp")
    OUT.mkdir(parents=True, exist_ok=True)

    android = Image.new("RGBA", CANVAS, (0, 0, 0, 255))
    android_bg(android, bg)
    android_imageview(android, home)
    android.save(OUT / "compare_android_style.webp_layers.png", optimize=True)

    ha = Image.new("RGBA", CANVAS, (0, 0, 0, 255))
    css_contain_bottom(ha, bg)
    css_contain_bottom(ha, home)
    ha.save(OUT / "compare_ha_css_style.png", optimize=True)

    # Raw webp pasted 1:1 if smaller than canvas (no scaling)
    raw = Image.new("RGBA", CANVAS, (0, 0, 0, 255))
    raw.paste(bg, ((CANVAS[0] - bg.width) // 2, CANVAS[1] - bg.height), bg)
    raw.alpha_composite(home, ((CANVAS[0] - home.width) // 2, CANVAS[1] - home.height))
    raw.save(OUT / "compare_native_size_bottom.png", optimize=True)

    print(f"bg webp {bg.size}, home webp {home.size}")
    print(f"wrote {OUT}/compare_*.png")


if __name__ == "__main__":
    main()
