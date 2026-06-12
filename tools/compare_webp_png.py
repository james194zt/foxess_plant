#!/usr/bin/env python3
"""Compare Fox APK webp vs HA www PNG dimensions and alpha."""
from pathlib import Path

from PIL import Image

APK = Path("/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/res/mipmap-nodpi-v4")
WWW = Path(__file__).resolve().parents[1] / "custom_components/foxess_plant/www"
THEME = "day_light"

pairs = [
    ("flow_home_bg", f"flow_home_bg_{THEME}"),
    ("flow_home", f"flow_home_{THEME}"),
    ("flow_pv", f"flow_pv_{THEME}"),
    ("flow_aio", f"flow_aio_812_{THEME}"),
]

for label, base in pairs:
    webp = APK / f"{base}.webp"
    png = WWW / f"{base}.png"
    print(f"\n=== {label} ===")
    for path in (webp, png):
        if not path.is_file():
            print(f"  MISSING {path.name}")
            continue
        im = Image.open(path)
        mode = im.mode
        if mode != "RGBA":
            im = im.convert("RGBA")
        a = im.getchannel("A")
        lo, hi = a.getextrema()
        transparent = sum(1 for p in a.getdata() if p == 0)
        total = im.size[0] * im.size[1]
        print(
            f"  {path.name}: {im.size[0]}x{im.size[1]} mode={mode} "
            f"alpha={lo}-{hi} transparent={transparent}/{total} ({100*transparent/total:.1f}%) "
            f"bytes={path.stat().st_size}"
        )
