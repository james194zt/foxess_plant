#!/usr/bin/env python3
import re
import urllib.request

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
).read().decode("utf-8", "replace")

NEED = [
    "icon-e_grid_import",
    "icon-e_grid_export",
    "icon-icon-discharge",
    "icon-icon-charge",
    "icon-icon-load",
    "icon-plantHome",
    "icon-icon-battery",
    "icon-e_solar",
    "icon-solar",
    "icon-pv",
    "icon-generated",
    "icon-e_pv",
    "icon-d-pv",
    "icon-icon-solar",
    "icon-icon-pv",
    "icon-produce",
]

def extract(icon_id):
    m = re.search(
        rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'',
        app,
    )
    return m.group(1) if m else None

for icon_id in NEED:
    content = extract(icon_id)
    if content:
        print("FOUND", icon_id)
        print(content[:2000])
        print()

for m in re.finditer(r'id:"(icon-[^"]+)"', app):
    n = m.group(1)
    if any(k in n.lower() for k in ["solar", "pv", "sun", "produce", "generat"]):
        print("solarish", n)
        c = extract(n)
        if c and len(c) < 3000:
            print(c[:1500])
            print()

# extract icon-icon-charge and icon-icon-load fully
for icon_id in ["icon-icon-charge", "icon-icon-load", "icon-plantHome", "icon-icon-solar", "icon-e_pv", "icon-d-pv1"]:
    c = extract(icon_id)
    if c:
        print("=== FULL", icon_id, "len", len(c))
