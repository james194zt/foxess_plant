#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
rt_m = re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index)
rt = fetch("https://www.foxesscloud.com" + rt_m.group(1))
print("runtime", rt_m.group(1), "len", len(rt))

for pat in [r'8441:"([a-f0-9]+)"', r'"8441":"([a-f0-9]+)"', r"8441-([a-f0-9]+)", r"8441\.([a-f0-9]+)\.js"]:
    ms = re.findall(pat, rt)
    if ms:
        print(pat, ms[:5])

# search all chunk id patterns in runtime
ids = re.findall(r"(\d{3,5}):\"([a-f0-9]{8,})\"", rt)
print("id:hash pairs", len(ids))
for cid, h in ids:
    if cid == "8441":
        print("FOUND", cid, h)

# also search app for module 56336 from route
app_m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index)
app = fetch("https://www.foxesscloud.com" + app_m.group(1))
for m in re.finditer(r"8441.{0,30}", app):
    s = m.group(0)
    if len(s) < 50:
        print("app ref:", s)

# search minTemperature in full app - might be inlined
for kw in ["minTemperature", "pvPower", "batSoc"]:
    if kw not in app:
        print(kw, "NOT in app")
        continue
    i = app.find(kw)
    while i >= 0 and i < len(app):
        sn = app[max(0,i-100):i+500]
        if "icon" in sn.lower() or "svg" in sn.lower() or "class" in sn.lower():
            print(f"\n{kw}:")
            print(sn[:600])
            break
        i = app.find(kw, i+1)
