#!/usr/bin/env python3
"""Find which Fox chunk maps summary cards to icon-d-battery1..4."""
import re
import urllib.request


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")


index = fetch("https://www.foxesscloud.com/v2/")
app_m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index)
app = fetch("https://www.foxesscloud.com" + app_m.group(1))
rt_m = re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index)
rt = fetch("https://www.foxesscloud.com" + rt_m.group(1))

chunks = sorted(set(re.findall(r'"(\d+\.[a-f0-9]+\.js)"', app)))
print(f"{len(chunks)} chunks in app")

hits = []
for chunk in chunks:
    url = f"https://www.foxesscloud.com/v2/assets/js/{chunk}"
    try:
        js = fetch(url)
    except Exception:
        continue
    if "icon-d-battery1" not in js:
        continue
    # skip pure icon definition chunks (webpack modules registering svg)
    if js.count("icon-d-battery1") == 1 and "pvPower" not in js and "batSoc" not in js:
        continue
    hits.append((chunk, js))

print(f"chunks with icon-d-battery1 usage: {len(hits)}")
for chunk, js in hits:
    print("\nCHUNK", chunk, "len", len(js))
    for kw in ["pvPower", "batSoc", "discharging", "minTemperature", "icon-d-battery"]:
        if kw in js:
            print("  has", kw)
    for m in re.finditer(r".{0,120}icon-d-battery[1-4].{0,120}", js):
        s = m.group(0)
        if "content:" in s or "viewBox" in s:
            continue
        print("  ctx:", s[:220])
