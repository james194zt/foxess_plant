#!/usr/bin/env python3
import re
import urllib.request
from pathlib import Path

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
).read().decode("utf-8", "replace")

ICON_IDS = [
    "icon-e_grid_import",
    "icon-e_grid_export",
    "icon-e_solar",
    "icon-solar",
    "icon-pv",
    "icon-battery",
    "icon-icon-discharge",
    "icon-charger",
    "icon-home",
    "icon-house",
    "icon-e_home",
    "icon-load",
]

for icon_id in ICON_IDS:
    pat = rf'id:"{re.escape(icon_id)}"'
    if pat.replace("\\", "") in app or icon_id in app:
        m = re.search(
            rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'',
            app,
        )
        if m:
            print("===", icon_id, "===")
            print(m.group(1)[:1200])
            print()

# broader search for energy analysis icons
for m in re.finditer(
    r'id:"(icon-e_grid_import|icon-e_grid_export|icon-e_solar[^"]*|icon-e_pv[^"]*|icon-battery[^"]*|icon-icon-discharge|icon-e_home[^"]*|icon-home[^"]*|icon-charge[^"]*)"',
    app,
):
    icon_id = m.group(1)
    m2 = re.search(
        rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'',
        app[m.start() : m.start() + 4000],
    )
    if m2:
        print("===", icon_id, "===")
        print(m2.group(1)[:1500])
        print()

# search produced / sun icon used in analysis
for pat in ["icon-e_solar", "icon-solar_power", "icon-pv_pro", "icon-generated", "icon-sun"]:
    if pat in app:
        print("found id string", pat)

for m in re.finditer(r'id:"icon-[^"]*(?:solar|pv|sun|produce)[^"]*"', app, re.I):
    print("candidate", m.group(0))

for m in re.finditer(r'id:"icon-[^"]*(?:home|house|load|consume)[^"]*"', app, re.I):
    print("home candidate", m.group(0))

for m in re.finditer(r'id:"icon-[^"]*(?:charge|battery|discharge)[^"]*"', app, re.I):
    print("bat candidate", m.group(0))

out = Path("/mnt/c/Users/James/Documents/repo/foxess_plant/tools/fox_analysis_icons.txt")
chunks = []
for m in re.finditer(
    r'id:"(icon-e_grid_import|icon-e_grid_export)"[^}}]*content:\'([^\']+)\'',
    app,
):
    chunks.append(f"{m.group(1)}\n{m.group(2)}\n")
out.write_text("\n".join(chunks), encoding="utf-8")
print("wrote", out)
