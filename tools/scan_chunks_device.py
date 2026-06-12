#!/usr/bin/env python3
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch(u):
    r = urllib.request.Request(
        u,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Referer": "https://www.foxesscloud.com/v2/",
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        data = resp.read().decode("utf-8", "replace")
        if data.startswith("<!"):
            return None
        return data

index = fetch("https://www.foxesscloud.com/v2/")
rt_url = "https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index).group(1)
rt = fetch(rt_url)
pairs = list(set(re.findall(r"(\d+):\"([a-f0-9]+)\"", rt)))
print("chunks", len(pairs))

needles = ["pvPower", "batSoc", "minTemperature", "DischargePower", "icon-minSoc", "icon-drier", "icon-icon-discharge"]

def scan(pair):
    cid, h = pair
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        return None
    if not js:
        return None
    hits = [n for n in needles if n in js]
    if hits:
        return cid, h, len(js), hits, js
    return None

results = []
with ThreadPoolExecutor(max_workers=12) as ex:
    futs = [ex.submit(scan, p) for p in pairs]
    for f in as_completed(futs):
        r = f.result()
        if r:
            results.append(r)

results.sort(key=lambda x: -x[2])
for cid, h, ln, hits, js in results:
    print(f"\n=== {cid}.{h}.js len={ln} hits={hits} ===")
    for t in hits:
        i = js.find(t)
        print(f"-- {t} --")
        print(js[max(0, i - 120) : i + 500][:620])
