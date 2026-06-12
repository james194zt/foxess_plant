#!/usr/bin/env python3
import re
import urllib.request

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js",
    timeout=120,
).read().decode("utf-8", "replace")

# English block anchor
m = re.search(r'en:\{common:\{edit:"Edit"', app)
block = app[m.start() : m.start() + 30000]

for pat in [
    r'loadLabel(\d+):"([^"]+)"',
    r'gridLabel(\d+):"([^"]+)"',
    r'batLabel(\d+):"([^"]+)"',
    r'(loadInfo|gridInfo|batteryInfo|dataloggerInfo):"([^"]+)"',
    r'(signalStrength|softwareVersion|capacity|remainingCapacity|nominalLabel|general|health|expectedLife|harmfulEvents|chargeThroughput|dischargeThroughput|fullEquivalent|deepDischarge|extremeTemp|dateOfManufacture|ohmicResistance|selfDischarg|roundTrip|remainingPower):"([^"]+)"',
]:
    for mm in re.finditer(pat, block):
        print(f"{mm.group(1)}: {mm.group(2)}")

# bat labels extended search whole app for batGeneral etc
for term in ["batGeneral", "batHealth", "General", "Health", "Expected life", "signalStrength", "Signal strength", "Software Version", "dataloggerInfo"]:
    for m in re.finditer(re.escape(term), app):
        i = m.start()
        if i < 1300000 or i > 1400000:
            continue
        sn = app[max(0, i - 80) : i + 120]
        if "function" not in sn:
            print(f"\n{term}@{i}: {sn[:180]}")
