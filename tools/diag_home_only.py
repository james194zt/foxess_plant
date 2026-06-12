#!/usr/bin/env python3
from pathlib import Path
from PIL import Image

WWW = Path(__file__).resolve().parents[1] / "custom_components/foxess_plant/www"
OUT = Path(__file__).resolve().parent / "flow_scene_preview"
from key_flow_home_sky import remove_black_matte_only, CANVAS

theme = "day_dark"
home = Image.open(WWW / f"flow_home_{theme}.png").convert("RGBA")
if home.size != CANVAS:
    home = home.resize(CANVAS, Image.Resampling.LANCZOS)
home = remove_black_matte_only(home)
bg = Image.new("RGBA", CANVAS, (40, 40, 40, 255))
bg.alpha_composite(home)
bg.save(OUT / f"home_only_{theme}.png")
print("wrote home_only")
