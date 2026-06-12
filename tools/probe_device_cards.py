#!/usr/bin/env python3
import re
import urllib.request

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
).read().decode("utf-8", "replace")

patterns = [
    r"pvPower[^}]{0,400}",
    r"batSoc[^}]{0,400}",
    r"minTemperature[^}]{0,400}",
    r"discharg[^}]{0,200}",
    r"icon-icon-phot[^}]{0,100}",
]
for pat in patterns:
    for m in re.finditer(pat, app):
        s = m.group(0).replace("\n", " ")
        if "icon" in s.lower() or "svg" in s.lower() or "color" in s.lower():
            print("---", pat)
            print(s[:450])

# brute: find arrays with pvPower and icon
for m in re.finditer(r"\[[^\]]{0,200}pvPower[^\]]{0,800}\]", app):
    s = m.group(0)
    if "icon" in s:
        print("ARRAY", s[:600])
