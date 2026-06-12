#!/usr/bin/env python3
import re
import urllib.request

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
).read().decode("utf-8", "replace")

patterns = [
    "Imported",
    "PV Produced",
    "Discharged",
    "Exported",
    "Consumed",
    "Charged",
    "eenery_stat",
    "svg-block",
    "flow_l",
    "eenery_stat_flow",
    "2146a659",
]
for p in patterns:
    print(p, app.count(p))

# context around Imported
for m in re.finditer("Imported", app):
    i = m.start()
    print("--- Imported ctx ---")
    print(app[i - 300 : i + 500])
    break

# search icon svg viewBox 32
for pat in [r"viewBox:\"0 0 32 32\"", r'viewBox:"0 0 32 32"']:
    print(pat, app.count(pat))

# find svg strings with tower/grid/sun/battery keywords in nearby text
for kw in ["grid", "solar", "battery", "house", "tower", "import", "export", "charge", "discharge"]:
    for m in re.finditer(kw, app, re.I):
        i = m.start()
        chunk = app[max(0, i - 100) : i + 200]
        if "viewBox" in chunk or "svg" in chunk.lower():
            print("KW", kw, chunk[:250])
            break

# webpack async chunk 4264 reference with module content in app?
idx = app.find("4264:")
print("4264 refs", app.count("4264:"))
print(app[app.find("plants-analysis") - 100 : app.find("plants-analysis") + 300])
