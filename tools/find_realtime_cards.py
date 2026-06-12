#!/usr/bin/env python3
import re
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
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
    if "DischargePower" not in js or len(js) < 5000 or js.startswith("<!"):
        continue
    print(f"\n=== chunk {cid}.{h}.js len={len(js)} ===")
    for term in ["DischargePower", "pvPower", "batSoc", "minTemperature", "icon-d-battery", "topColor", "topLine", "bgColor", "cardColor", "linear-gradient"]:
        if term in js:
            i = 0
            n = 0
            while n < 3:
                pos = js.find(term, i)
                if pos < 0:
                    break
                sn = js[max(0, pos - 120) : pos + 280].replace("\n", " ")
                print(f"[{term}]", sn[:360])
                i = pos + len(term)
                n += 1
