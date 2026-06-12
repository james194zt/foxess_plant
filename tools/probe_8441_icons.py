#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

for h in ["d6c0ed22", "9decfb0b"]:
    url = f"https://www.foxesscloud.com/v2/assets/js/8441.{h}.js"
    print("\n========", url)
    try:
        js = fetch(url)
    except Exception as e:
        print("fail", e)
        continue
    print("len", len(js))
    for kw in ["pvPower", "batSoc", "minTemperature", "discharging", "icon-icon-phot", "icon-drier", "icon-minSoc", "icon-icon-discharge", "summaryList", "cardList", "realCard"]:
        if kw in js:
            print(" has", kw)
            i = js.find(kw)
            print(js[max(0,i-120):i+450][:550])

    # find objects with icon property
    for m in re.finditer(r"icon:\"(icon-[^\"]+)\"", js):
        print("icon ref:", m.group(1))

    for m in re.finditer(r"icon:([a-zA-Z_$][\w$]*)", js):
        name = m.group(1)
        if name not in ("icon", "icons"):
            print("icon var:", name)
