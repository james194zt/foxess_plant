#!/usr/bin/env python3
from io import BytesIO
from pathlib import Path

from PIL import Image
from rembg import remove

src = Path(
    "/mnt/c/Users/James/.cursor/projects/c-Users-James-Documents-repo-HADashboard/assets/"
    "c__Users_James_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_"
    "image-9facf1d9-f83c-457e-b0ef-7d8446a6bb00.png"
)
dst = Path("/mnt/c/Users/James/Documents/repo/foxess_plant/custom_components/foxess_plant/www/evo10.png")

data = remove(src.read_bytes())
img = Image.open(BytesIO(data)).convert("RGBA")
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
