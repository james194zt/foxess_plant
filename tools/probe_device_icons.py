#!/usr/bin/env python3
import re
import urllib.request

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
).read().decode("utf-8", "replace")

for key in ["pvPow", "batSoc", "discharging", "minTemperature", "minTemp", "pvPower"]:
    i = app.find(key)
    print(key, i)

# Search lazy chunk for device details
m = re.search(r"path:\"/plants/deviceDetails\".*?t\.e\((\d+)\)", app)
if m:
    print("deviceDetails chunk", m.group(1))

# Find card list patterns near batSoc
i = app.find("batSoc")
print(app[max(0, i - 200) : i + 500])

# Search all icons with 'temp' in id from symbol definitions
for cid in sorted(set(re.findall(r'id:"(icon-[^"]+)"', app))):
    if re.search(r"temp|therm|weather|celsius|degree", cid, re.I):
        print("temp icon", cid)
