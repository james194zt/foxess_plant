#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

app = fetch("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js")

def extract_symbol(app_text, icon_id):
    m = re.search(rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'', app_text)
    if not m:
        return None
    raw = m.group(1).replace("\\n", "\n")
    raw = re.sub(r"<symbol([^>]*)>", r"<svg\1>", raw, count=1)
    raw = raw.replace("</symbol>", "</svg>")
    if 'xmlns="http://www.w3.org/2000/svg"' not in raw:
        raw = raw.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return raw

for iid in ["icon-minSoc", "icon-icon-discharge", "icon-drier_iocn", "icon-icon-phot", "icon-icon-battery", "icon-discharging"]:
    svg = extract_symbol(app, iid)
    print("\n===", iid, "len", len(svg or ""), "===")
    if svg:
        # show fill colors and path hints
        fills = re.findall(r'fill="([^"]+)"', svg)[:8]
        print("fills", fills)
        print(svg[:400])

# search usage of minSoc icon in app (not definition)
for m in re.finditer(r"icon-minSoc-usage|icon-class:\"minSoc\"|\"minSoc\"", app):
    i = m.start()
    print("\nUSAGE:", app[max(0, i - 200) : i + 300][:450])
