#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

app = fetch("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js")

# Skip icon registration blocks (77286:function pattern with id:"icon-)
for term in ["icon-phot", "icon-battery", "icon-discharge", "minSoc", "drier_iocn"]:
    pos = 0
    n = 0
    while n < 20:
        i = app.find(term, pos)
        if i < 0:
            break
        ctx = app[max(0, i - 120) : i + 200]
        if 'id:"icon-' in ctx or "content:'<symbol" in ctx:
            pos = i + 1
            continue
        print(f"\n--- {term} @ {i} ---")
        print(ctx[:320])
        pos = i + 1
        n += 1

# device card list patterns
for pat in [
    r"icon:\"icon-icon-phot\"",
    r"icon:\"icon-icon-battery\"",
    r"icon:\"icon-icon-discharge\"",
    r"icon:\"icon-minSoc\"",
    r"iconClass:\"icon-icon-phot\"",
    r'"icon-icon-phot"',
    r'"icon-minSoc"',
]:
    if pat.strip('"') in app or pat in app:
        i = app.find(pat.replace('\\"', '"').strip('"') if False else pat.split('"')[1] if '"' in pat else pat)
        # simpler
    for m in re.finditer(re.escape(pat.replace('\\"', '"')) if pat.startswith('icon:') else pat, app):
        pass

for m in re.finditer(r'icon:"(icon-[^"]+)"', app):
    name = m.group(1)
    if any(x in name for x in ["phot", "battery", "discharge", "minSoc", "drier", "Soc"]):
        i = m.start()
        print("\nicon prop:", name, app[max(0,i-150):i+200][:300])

# card array with key field names
for m in re.finditer(r"key:\"(pvPower|batSoc|minTemperature|discharge[^\"]*)\"", app):
    i = m.start()
    print("\nkey:", m.group(1), app[max(0,i-100):i+350][:400])
