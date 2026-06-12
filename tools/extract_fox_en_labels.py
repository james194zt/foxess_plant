#!/usr/bin/env python3
import re, urllib.request
app = urllib.request.urlopen("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120).read().decode("utf-8","replace")
# Find English locale block
m = re.search(r"en:\{common:\{edit:\"Edit\"", app)
if not m:
    m = re.search(r'en:\{[^}]*common:\{edit:"Edit"', app)
start = m.start() if m else app.find('realTime:"Real-time"') - 500
block = app[start:start+25000]
for pat in [
    r'loadLabel(\d):"([^"]+)"',
    r'gridLabel(\d):"([^"]+)"',
    r'batLabel(\d):"([^"]+)"',
    r'(pvInfo|acInfo|epsInfo|loadInfo|gridInfo|batteryInfo|dataloggerInfo):"([^"]+)"',
    r'(pvPower|batSoc|acPower|minTemperature|realTimeCurve|energyAnalysis):"([^"]+)"',
    r'(voltage|current|power|frequency|state|meter|datalogger):"([^"]+)"',
]:
    for mm in re.finditer(pat, block):
        print(f"{mm.group(1)}: {mm.group(2) if mm.lastindex==2 else mm.group(0)}")
