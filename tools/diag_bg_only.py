#!/usr/bin/env python3
from pathlib import Path
from PIL import Image

WWW = Path(__file__).resolve().parents[1] / "custom_components/foxess_plant/www"
OUT = Path(__file__).resolve().parent / "flow_scene_preview"
CANVAS = (1024, 1017)
theme = "day_dark"

for name in (f"flow_home_bg_{theme}.png", f"flow_home_bg_scene_{theme}.png"):
    im = Image.open(WWW / name).convert("RGBA")
    scale = max(CANVAS[0] / im.width, CANVAS[1] / im.height)
    nw, nh = int(im.width * scale), int(im.height * scale)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", CANVAS, (40, 40, 40, 255))
    x = (CANVAS[0] - nw) // 2
    y = CANVAS[1] - nh
    bg.paste(im, (x, y), im)
    out = OUT / name.replace(".png", "_preview.png")
    bg.save(out)
    print("wrote", out.name, "from", name)
