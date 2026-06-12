#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
    with urllib.request.urlopen(r, timeout=120) as resp:
        ct = resp.headers.get("content-type", "")
        data = resp.read().decode("utf-8", "replace")
        return data, ct

index, _ = fetch("https://www.foxesscloud.com/v2/")
rt_m = re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index)
rt, _ = fetch("https://www.foxesscloud.com" + rt_m.group(1))
h = re.search(r'8441:"([a-f0-9]+)"', rt).group(1)
url = f"https://www.foxesscloud.com/v2/assets/js/8441.{h}.js"
js, ct = fetch(url)
print("content-type", ct, "len", len(js), "starts", js[:80])

for kw in ["pvPower", "batSoc", "minTemperature", "discharging", "56336", "icon"]:
    print(kw, kw in js)

# find parent chunks that 8441 imports
for m in re.finditer(r"t\.e\((\d+)\)", js):
    print("lazy chunk", m.group(1))

# search app for device card render - look for minTemperature label key in vue template
app_m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index)
app, _ = fetch("https://www.foxesscloud.com" + app_m.group(1))

# Find discharging power label
for label in ["Discharging power", "dischargingPower", "minTemperature", "Min. Battery Temperature"]:
    if label in app:
        i = app.find(label)
        print(f"\n{label} @ {i}:")
        print(app[max(0,i-200):i+500])

# Search for icon PNG paths in app related to device
for m in re.finditer(r"/v2/assets/[^\"']+\.(?:png|svg)", app):
    p = m.group(0)
    if any(x in p.lower() for x in ["phot", "battery", "discharg", "temp", "drier", "device", "pv", "soc"]):
        print("asset", p)

# card icon class patterns
for m in re.finditer(r"className:\"[^\"]*icon[^\"]*\"", app):
    s = m.group(0)
    if len(s) < 120:
        print(s)
