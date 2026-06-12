#!/usr/bin/env python3
import re
import urllib.request


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")


index = fetch("https://www.foxesscloud.com/v2/")
rt = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index).group(1))
chunks = dict(re.findall(r'(\d+):"([a-f0-9]+)"', rt))
for cid, h in chunks.items():
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        continue
    if "icon-d-battery1" not in js:
        continue
    if "content:'<symbol" in js and "pvPower" not in js:
        continue
    print("HIT", cid, url, len(js))
    for kw in ["pvPower", "batSoc", "DischargePower", "minTemperature", "icon-d-battery1", "icon-d-battery2"]:
        if kw in js:
            i = js.find(kw)
            print(" ", kw, js[max(0, i - 80) : i + 120])
