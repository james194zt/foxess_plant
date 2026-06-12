#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
app_m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index)
app_url = "https://www.foxesscloud.com" + app_m.group(1)
app = fetch(app_url)
rt_m = re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index)
rt = fetch("https://www.foxesscloud.com" + rt_m.group(1))

hash_m = re.search(r'"8441"\s*:\s*"([a-f0-9]+)"', rt) or re.search(r"8441:\"([a-f0-9]+)\"", app)
if not hash_m:
    print("chunk hash not found")
    raise SystemExit(1)
h = hash_m.group(1)
chunk_url = f"https://www.foxesscloud.com/v2/assets/js/8441.{h}.js"
print("chunk", chunk_url)
js = fetch(chunk_url)

for kw in ["pvPower", "batSoc", "minTemperature", "discharging", "icon", "summary"]:
    idx = 0
    n = 0
    while n < 8:
        i = js.find(kw, idx)
        if i < 0:
            break
        snippet = js[max(0, i - 80) : i + 350]
        print(f"\n--- {kw} @ {i} ---")
        print(snippet)
        idx = i + len(kw)
        n += 1

# card list pattern
for m in re.finditer(r"\{[^{}]{0,40}icon:[^{}]{0,120}\}", js):
    s = m.group(0)
    if any(k in s for k in ["phot", "battery", "discharg", "drier", "minSoc", "Soc", "temp"]):
        print("\nCARD", s[:300])
