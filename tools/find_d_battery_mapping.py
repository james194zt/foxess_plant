#!/usr/bin/env python3
import re
import urllib.request


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")


index = fetch("https://www.foxesscloud.com/v2/")
app_m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index)
app = fetch("https://www.foxesscloud.com" + app_m.group(1))

# Find contexts where multiple d-battery icons appear together
for m in re.finditer(r"icon-d-battery[1-4]", app):
    start = max(0, m.start() - 400)
    end = min(len(app), m.end() + 400)
    snippet = app[start:end]
    if snippet.count("icon-d-battery") >= 2:
        print("=== multi-hit @", m.start(), "===")
        print(snippet)
        print()

# Search for summary / realtime card config keys near icons
for kw in [
    "pvPower",
    "batSoc",
    "discharging",
    "minTemperature",
    "Min. Battery Temperature",
    "summary",
    "realTime",
    "deviceDetails",
]:
    if kw not in app:
        continue
    print(f"\n### keyword {kw} ###")
    pos = 0
    n = 0
    while n < 3:
        i = app.find(kw, pos)
        if i < 0:
            break
        print(app[max(0, i - 120) : i + 280])
        print("---")
        pos = i + len(kw)
        n += 1
