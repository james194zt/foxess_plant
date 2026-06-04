#!/usr/bin/env python3
"""Tight-crop evo10.png to visible device pixels (trim transparent padding)."""
from pathlib import Path

from PIL import Image

path = Path(__file__).resolve().parents[1] / "custom_components/foxess_plant/www/evo10.png"
img = Image.open(path).convert("RGBA")
bbox = img.getbbox()
if not bbox:
    raise SystemExit("empty image")
# Trim a few px of soft edge shadow only; keep device silhouette tight.
pad = 4
left = max(0, bbox[0] - pad)
top = max(0, bbox[1] - pad)
right = min(img.width, bbox[2] + pad)
bottom = min(img.height, bbox[3] + pad)
cropped = img.crop((left, top, right, bottom))
print(f"before {img.size} bbox {bbox} -> after {cropped.size}")
cropped.save(path, "PNG", optimize=True)
print("saved", path)
