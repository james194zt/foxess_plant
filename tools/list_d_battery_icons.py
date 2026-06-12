#!/usr/bin/env python3
import re
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")

def extract(app, icon_id):
    m = re.search(rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'', app)
    if not m:
        return None
    raw = m.group(1)
    colors = re.findall(r'fill="(#[0-9A-Fa-f]{3,8})"', raw)
    return colors[:5]

index = fetch("https://www.foxesscloud.com/v2/")
app = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index).group(1))

for i in range(1, 8):
    cid = f"icon-d-battery{i}"
    colors = extract(app, cid)
    print(cid, colors or "MISSING")

# search usage strings
for m in re.finditer(r'icon-d-battery[1-7]', app):
    sn = app[max(0,m.start()-60):m.end()+60]
    if "content:" in sn or "viewBox" in sn:
        continue
    print("usage", sn)
    break
