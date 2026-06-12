#!/usr/bin/env python3
from pathlib import Path

from PIL import Image

WWW = Path(__file__).resolve().parent.parent / "custom_components/foxess_plant/www"
for name in ("flow_home_day_light.png", "flow_home_bg_day_light.png"):
    im = Image.open(WWW / name).convert("RGBA")
    a = im.getchannel("A")
    lo, hi = a.getextrema()
    transparent = sum(1 for p in a.getdata() if p == 0)
    print(f"{name}: size={im.size} alpha={lo}-{hi} transparent_px={transparent}")
