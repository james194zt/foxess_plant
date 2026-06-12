#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

app = fetch("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js")

# property access patterns
for pat in [r"\.pvPower", r"pvPower,", r"pvPower:", r'"pvPower"', r"'pvPower'"]:
    count = len(re.findall(pat, app))
    if count:
        print(pat, count)

# find pvPower not in i18n (exclude pvPower:"PV Power")
for m in re.finditer(r"pvPower", app):
    i = m.start()
    sn = app[i : i + 30]
    if sn.startswith('pvPower:"PV Power"') or sn.startswith('pvPower:"'):
        continue
    ctx = app[max(0, i - 250) : i + 400]
    if "PV Power" in ctx:
        continue
    print("\n=== pvPower @", i, "===")
    print(ctx[:550])
    break

# Search cardList / topList / dataList arrays
for m in re.finditer(r"(?:card|data|top|summary|real)[A-Z][a-zA-Z]{2,20}List", app):
    term = m.group(0)
    if app.count(term) < 50:
        i = app.find(term)
        print(f"\n{term}:", app[max(0,i-50):i+400][:450])

# icon png paths - list all ./icon*.svg mappings
for m in re.finditer(r'"\./(icon[^"]+\.svg)":(\d+)', app):
    name, mod = m.group(1), m.group(2)
    if any(x in name for x in ["phot", "battery", "discharge", "temp", "drier", "soc", "charge"]):
        print(f"svg module {mod}: {name}")
