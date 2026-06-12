#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

css = fetch("https://www.foxesscloud.com/v2/assets/css/app.8a3957c4.css")
print("css len", len(css))

terms = [
    "deviceDetail", "device-detail", "realTime", "real-time", "topCard", "top-card",
    "dataCard", "data-card", "summaryCard", "cardItem", "card-item", "iconBox",
    "icon-box", "overviewCard", "statCard", "indexCard", "phot", "minSoc",
    "discharge", "deviceInfo", "device-info", "aioDetail",
]
for t in terms:
    if t in css:
        print(f"\n=== {t} ({css.count(t)} hits) ===")
        idx = 0
        for _ in range(min(3, css.count(t))):
            i = css.find(t, idx)
            print(css[max(0, i - 80) : i + 180][:260])
            idx = i + 1

# list img assets in app js
app = fetch("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js")
for m in re.finditer(r"/v2/assets/img/[^\"']+", app):
    p = m.group(0)
    if any(x in p.lower() for x in ["phot", "battery", "temp", "discharg", "pv", "soc", "device", "card"]):
        print("img", p)

# search vue render for device top cards - look for class strings
for m in re.finditer(r'class:"[^"]{0,60}(?:card|Card|data|Data|real|Real)[^"]{0,60}"', app):
    s = m.group(0)
    if any(x in s.lower() for x in ["device", "detail", "real", "top", "index", "stat"]):
        if s not in ('class:"statistics-chart-wrap"',):
            print("class", s[:120])
