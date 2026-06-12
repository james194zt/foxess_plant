#!/usr/bin/env python3
import re
import urllib.request

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
).read().decode("utf-8", "replace")

# module ids for work mode svgs
mods = {
    "workMode1": 53576,
    "workMode2": 34939,
    "workMode3": 17098,
    "workMode4": 27509,
    "peakShaving": 34864,
    "feedPriority": 27689,
    "backup": 85031,
    "charge": None,
    "discharge": None,
}

for name, mid in mods.items():
    if not mid:
        continue
    pat = f"t({mid})"
    print(f"{name} ({mid}): {app.count(pat)} refs")
    idx = 0
    shown = 0
    while shown < 2:
        idx = app.find(pat, idx + 1)
        if idx < 0:
            break
        ctx = app[max(0, idx - 500) : idx + 500]
        if "selfUse" in ctx or "feedIn" in ctx or "backUp" in ctx or "peakShaving" in ctx or "mode" in ctx.lower():
            print(f"  ctx: {ctx[:700]}")
            shown += 1

# search for mode value constants with icon property
for m in re.finditer(r"selfUse[^\n]{0,200}workMode1|workMode1[^\n]{0,200}selfUse", app):
    print("direct map:", m.group()[:200])

# broader: find object keys with icon imports near mode names
for m in re.finditer(r"\{value:[^}]{0,300}selfUse[^}]{0,300}\}", app):
    print("obj:", m.group()[:400])

# search SelectWorkMode or similar
for term in ["SelectWorkMode", "WorkModeSelect", "workModeList", "modeList", "basicList", "getModeIcon"]:
    if term in app:
        idx = app.find(term)
        print(f"\n{term}:", app[idx:idx+1200][:1000])
