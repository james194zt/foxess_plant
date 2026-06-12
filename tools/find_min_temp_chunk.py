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
    if "minTemperature" not in js or js.startswith("<!"):
        continue
    print(f"\nchunk {cid}.{h}.js len={len(js)}")
    i = js.find("minTemperature")
    print(js[max(0,i-500):i+800][:1200])
