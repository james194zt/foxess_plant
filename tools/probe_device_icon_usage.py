#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(
        u,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/javascript, */*;q=0.1",
            "Referer": "https://www.foxesscloud.com/v2/",
        },
    )
    with urllib.request.urlopen(r, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
app_url = "https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index).group(1)
app = fetch(app_url)

terms = [
    "DischargePower",
    "Discharging power",
    "realTimeList",
    "realCard",
    "deviceCard",
    "summaryCard",
    "cardList",
    "topCard",
    "icon-icon-phot",
    "icon-drier",
    "icon-minSoc",
    "icon-icon-discharge",
    "svg-icon",
    "plantDeviceDetails",
]
for term in terms:
    count = app.count(term)
    if count:
        print(term, count)
        i = app.find(term)
        print(" ", app[max(0, i - 150) : i + 400][:500])
        print()

# Find vue component using DischargePower i18n key
for m in re.finditer(r"DischargePower", app):
    sn = app[m.start() - 400 : m.start() + 800]
    if "icon" in sn.lower() or "svg" in sn.lower() or "img" in sn.lower() or "class" in sn.lower():
        print("=== DischargePower usage ===")
        print(sn[:900])
        break

# Search for arrays mapping keys to icon component names
for m in re.finditer(r"\[[^\]]{0,60}pvPower[^\]]{0,400}\]", app):
    print("ARRAY", m.group(0)[:500])

# webpack: list all js files in runtime
rt_url = "https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index).group(1)
rt = fetch(rt_url)
# find chunks containing plantDeviceDetails or DischargePower
for cid, h in re.findall(r"(\d+):\"([a-f0-9]+)\"", rt):
    if cid not in ("8441", "8318", "6060", "56336"):
        continue
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        continue
    if js.startswith("<!"):
        continue
    hits = [t for t in ["DischargePower", "pvPower", "batSoc", "minTemperature", "icon-icon-phot", "56336"] if t in js]
    if hits:
        print(f"chunk {cid}.{h}.js len={len(js)} hits={hits}")
        for t in hits:
            i = js.find(t)
            print(js[max(0, i - 100) : i + 350][:400])
