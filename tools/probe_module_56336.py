#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
rt_m = re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index)
rt = fetch("https://www.foxesscloud.com" + rt_m.group(1))

# find hash for module 56336
for cid, h in re.findall(r'(\d+):\"([a-f0-9]+)\"', rt):
    if cid == "56336":
        print("56336", h)

# search app for 56336 chunk reference
app_m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index)
app = fetch("https://www.foxesscloud.com" + app_m.group(1))
for m in re.finditer(r"56336.{0,80}", app):
    print("app:", m.group(0)[:100])

# module 56336 might be in a different chunk - search all chunk files listed in runtime
hashes = {}
for cid, h in re.findall(r'(\d+):\"([a-f0-9]+)\"', rt):
    hashes.setdefault(cid, set()).add(h)

targets = [cid for cid in hashes if cid in ("56336", "8441", "8318", "6060")]
print("targets", targets)

# brute search app for minTemperature with icon nearby - wider window
kw = "minTemperature"
pos = 0
while True:
    i = app.find(kw, pos)
    if i < 0:
        break
    sn = app[max(0,i-300):i+600]
    if "icon" in sn or "Icon" in sn or "svg" in sn or "className" in sn:
        print("\n=== minTemperature context ===")
        print(sn)
    pos = i + 1

# search for card config arrays
for pat in [r"pvPower[^]]{0,800}\]", r"batSoc[^]]{0,800}\]", r"summaryCards[^]]{0,1200}\]"]:
    m = re.search(pat, app)
    if m:
        print("\n=== pattern", pat[:20], "===")
        print(m.group(0)[:900])
