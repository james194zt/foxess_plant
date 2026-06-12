#!/usr/bin/env python3
import re
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
app_m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index)
app = fetch("https://www.foxesscloud.com" + app_m.group(1))

# Usage refs (short) vs definitions (long content:'...)
for icon in [f"icon-d-battery{i}" for i in range(1, 5)]:
    print(f"\n=== {icon} usages (non-SVG) ===")
    count = 0
    for m in re.finditer(re.escape(icon), app):
        start = max(0, m.start() - 80)
        end = min(len(app), m.end() + 80)
        snippet = app[start:end]
        if "content:'" in snippet or "viewBox" in snippet:
            continue
        print(snippet)
        count += 1
        if count >= 8:
            break

# Look for array of summary metrics
for pat in [
    r"icon-d-battery1[^}]{0,300}icon-d-battery2",
    r"pvPower[^}]{0,200}icon-d-battery",
    r"batSoc[^}]{0,200}icon-d-battery",
    r"minTemperature[^}]{0,200}icon-d-battery",
    r"discharging[^}]{0,200}icon-d-battery",
]:
    m = re.search(pat, app, re.I)
    if m:
        print("\nPATTERN", pat)
        print(m.group(0)[:500])
