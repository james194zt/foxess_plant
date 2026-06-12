#!/usr/bin/env python3
import re
import urllib.request

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
).read().decode("utf-8", "replace")

def extract(icon_id):
    m = re.search(rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'', app)
    if not m:
        return None
    raw = m.group(1).replace("\\n", "\n")
    raw = re.sub(r"<symbol([^>]*)>", r"<svg\1>", raw, count=1)
    raw = raw.replace("</symbol>", "</svg>")
    if 'xmlns="http://www.w3.org/2000/svg"' not in raw:
        raw = raw.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return raw

ids = sorted(set(re.findall(r'id:"(icon-[^"]+)"', app)))
for i in ids:
    if re.search(r"drier|weather|celsius|degree|hot|cold|therm|minT|temp", i, re.I):
        print(i)

for cid in ["icon-discharging", "icon-drier_iocn", "icon-drier", "icon-minSoc"]:
    svg = extract(cid)
    print(cid, "OK" if svg else "NO", len(svg or ""))
