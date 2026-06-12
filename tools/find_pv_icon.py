#!/usr/bin/env python3
import re
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
app = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index).group(1))

# icons with Fox PV cyan or sun
for color in ["19D4DE", "894BFC", "03BD9A", "699BFF", "FA8C16", "52C41A"]:
    ids = []
    for m in re.finditer(rf'id:"(icon-[^"]+)"[^}}]*content:\'[^\']*{color}', app, re.I):
        ids.append(m.group(1))
    print(color, sorted(set(ids))[:15])

# search chunks for realTime card config object
rt = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index).group(1))
chunks = dict(re.findall(r'(\d+):"([a-f0-9]+)"', rt))
for cid, h in chunks.items():
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        continue
    if "realTimeList" in js or "realTimeDataList" in js or "topDataList" in js:
        print("chunk", cid, "realTime*")
        for term in ["realTimeList", "realTimeDataList", "topDataList"]:
            if term in js:
                i = js.find(term)
                print(js[i:i+800][:700])
