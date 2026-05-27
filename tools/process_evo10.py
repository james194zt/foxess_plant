#!/usr/bin/env python3
"""Remove near-white background from Evo product shot (no flood-fill)."""
from pathlib import Path

from PIL import Image

src = Path(
    "/mnt/c/Users/James/.cursor/projects/c-Users-James-Documents-repo-HADashboard/assets/"
    "c__Users_James_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_"
    "image-9facf1d9-f83c-457e-b0ef-7d8446a6bb00.png"
)
dst = Path("/mnt/c/Users/James/Documents/repo/foxess_plant/custom_components/foxess_plant/www/evo10.png")

img = Image.open(src).convert("RGBA")
px = img.load()
w, h = img.size

for y in range(h):
    for x in range(w):
        r, g, b, a = px[x, y]
        # Pure/near-white studio background only (device grey is much darker)
        if r >= 250 and g >= 250 and b >= 250:
            px[x, y] = (0, 0, 0, 0)
        elif r >= 245 and g >= 245 and b >= 245 and abs(r - g) < 6 and abs(g - b) < 6:
            px[x, y] = (0, 0, 0, 0)

bbox = img.getbbox()
if bbox:
    img = img.crop(bbox)

max_w = 400
if img.width > max_w:
    ratio = max_w / img.width
    img = img.resize((max_w, int(img.height * ratio)), Image.Resampling.LANCZOS)

dst.parent.mkdir(parents=True, exist_ok=True)
img.save(dst, "PNG", optimize=True)
print("saved", dst, img.size)
