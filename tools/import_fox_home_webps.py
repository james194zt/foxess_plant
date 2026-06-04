#!/usr/bin/env python3
"""Import flow_home_bg_* and flow_home_* from Fox APK webps (RGBA, alpha preserved)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

APK_RES = Path(
    "/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/res/mipmap-nodpi-v4"
)
WWW = Path(__file__).resolve().parents[1] / "custom_components/foxess_plant/www"
# Overlay sprites for all four Fox variants.
FLOW_OVERLAY_THEMES = ("day_light", "day_dark", "night_light", "night_dark")
IMPORT_THEMES = ("day_light", "day_dark", "night_light", "night_dark")


def dwebp(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["dwebp", str(src), "-o", str(dst)], check=True, capture_output=True)


def verify_rgba(path: Path) -> tuple[tuple[int, int], tuple[int, int], float]:
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    lo, hi = im.getchannel("A").getextrema()
    transparent = sum(1 for p in im.getchannel("A").get_flattened_data() if p == 0)
    total = im.size[0] * im.size[1]
    return im.size, (lo, hi), 100.0 * transparent / total


def main() -> int:
    if not APK_RES.is_dir():
        print(f"APK res missing: {APK_RES}", file=sys.stderr)
        return 1

    for theme in IMPORT_THEMES:
        for prefix in ("flow_home_bg", "flow_home"):
            src = APK_RES / f"{prefix}_{theme}.webp"
            dst = WWW / f"{prefix}_{theme}.png"
            if not src.is_file():
                print(f"skip missing {src.name}")
                continue
            dwebp(src, dst)
            size, alpha, pct = verify_rgba(dst)
            print(f"  {dst.name}: {size[0]}x{size[1]} alpha={alpha[0]}-{alpha[1]} transparent={pct:.1f}%")

    for theme in FLOW_OVERLAY_THEMES:
        for base, prefix in (("flow_pv", "flow_pv"), ("flow_aio_812", "flow_aio_812")):
            src = APK_RES / f"{prefix}_{theme}.webp"
            dst = WWW / f"{base}_{theme}.png"
            if not src.is_file():
                print(f"skip missing {src.name}")
                continue
            dwebp(src, dst)
            size, alpha, pct = verify_rgba(dst)
            print(f"  {dst.name}: {size[0]}x{size[1]} alpha={alpha[0]}-{alpha[1]} transparent={pct:.1f}%")

    print("Import done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
