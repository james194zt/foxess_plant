#!/usr/bin/env python3
"""Find Fox device summary card icon + style config from lazy chunks."""
import re
import urllib.request


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")


index = fetch("https://www.foxesscloud.com/v2/")
rt = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index).group(1))
chunks = dict(re.findall(r'(\d+):"([a-f0-9]+)"', rt))

keywords = [
    "pvPower",
    "batSoc",
    "DischargePower",
    "minTemperature",
    "icon-d-battery",
    "summaryList",
    "realTimeList",
    "topColor",
    "borderColor",
    "bgColor",
    "linear-gradient",
]

for cid, h in sorted(chunks.items(), key=lambda x: int(x[0])):
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        continue
    hits = [k for k in keywords if k in js]
    if not hits:
        continue
    if "icon-d-battery" not in js and "pvPower" not in js:
        continue
    print(f"\n=== chunk {cid}.{h}.js len={len(js)} hits={hits} ===")
    for kw in hits:
        pos = 0
        n = 0
        while n < 2:
            i = js.find(kw, pos)
            if i < 0:
                break
            sn = js[max(0, i - 150) : i + 350].replace("\n", " ")
            if kw == "icon-d-battery" or "icon" in sn or "color" in sn.lower() or "gradient" in sn.lower():
                print(f"  [{kw}]", sn[:420])
            pos = i + len(kw)
            n += 1
