#!/usr/bin/env python3
import re
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
app = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index).group(1))

# search for icon-d-battery usage outside svg definitions
for icon in ["icon-d-battery1", "icon-d-battery2", "icon-d-battery3", "icon-d-battery4"]:
    for m in re.finditer(re.escape(icon), app):
        sn = app[max(0,m.start()-200):m.end()+200]
        if "content:'" in sn or "viewBox" in sn or "Frame" in sn:
            continue
        print("USAGE", icon, sn)
        break

# search patterns for card config arrays
for pat in [
    r"icon-d-battery1.{0,500}icon-d-battery2.{0,500}icon-d-battery3",
    r"pvPower.{0,300}icon-d-battery",
    r"batSoc.{0,300}icon-d-battery",
    r"DischargePower.{0,300}icon-d-battery",
    r"minTemperature.{0,300}icon-d-battery",
    r"topLineColor.{0,200}",
    r"cardBgColor.{0,200}",
    r"cardTop.{0,200}",
]:
    m = re.search(pat, app, re.S)
    if m:
        print("\nPAT", pat[:40], m.group(0)[:600])

# search all chunks for icon-d-battery1-usage or iconClass
rt = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index).group(1))
chunks = dict(re.findall(r'(\d+):"([a-f0-9]+)"', rt))
for cid, h in chunks.items():
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        continue
    if "icon-d-battery1" in js and "content:'" not in js:
        print("chunk usage", cid, len(js))
        i = js.find("icon-d-battery1")
        print(js[max(0,i-150):i+250][:350])
