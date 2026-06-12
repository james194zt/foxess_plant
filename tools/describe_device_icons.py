#!/usr/bin/env python3
import re
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")

def extract(app, icon_id):
    m = re.search(rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'', app)
    return m.group(1) if m else None

index = fetch("https://www.foxesscloud.com/v2/")
app = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index).group(1))

for prefix in ["icon-d-battery", "icon-d-device", "icon-icon-phot", "icon-yieidT"]:
    for i in range(1, 8):
        cid = f"{prefix}{i}" if prefix != "icon-icon-phot" else prefix
        raw = extract(app, cid)
        if not raw:
            continue
        colors = sorted(set(re.findall(r'fill="(#[0-9A-Fa-f]{3,8})"', raw)))
        hints = []
        if "phot" in raw.lower() or "sun" in raw.lower() or "M13.97" in raw:
            hints.append("sun?")
        if "therm" in raw.lower() or "M22.398" in raw:
            hints.append("therm")
        if "lightning" in raw.lower() or "discharg" in raw.lower() or "M14.055" in raw:
            hints.append("bolt")
        if "battery" in raw.lower() or "Rectangle 34625968" in raw:
            hints.append("battery")
        print(cid, colors[:4], hints)
