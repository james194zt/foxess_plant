#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

app = fetch("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js")

# Find non-locale DischargePower usages (skip i18n block)
pos = 0
n = 0
while n < 15:
    i = app.find("DischargePower", pos)
    if i < 0:
        break
    # skip i18n dictionary (DischargePower:"Discharging power")
    sn = app[i : i + 80]
    if ':"Discharging power"' in sn:
        pos = i + 1
        continue
    ctx = app[max(0, i - 400) : i + 600]
    print(f"\n=== usage {n} @ {i} ===")
    print(ctx[:900])
    pos = i + 1
    n += 1

# Search icon-class patterns for device metrics
for m in re.finditer(r'icon-class:"([^"]+)"', app):
    cls = m.group(1)
    if any(x in cls.lower() for x in ["phot", "battery", "discharg", "soc", "temp", "drier", "min"]):
        i = m.start()
        print("\nicon-class", cls, app[max(0,i-80):i+120][:200])
