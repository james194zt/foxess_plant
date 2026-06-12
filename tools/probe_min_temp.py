#!/usr/bin/env python3
import urllib.request
app = urllib.request.urlopen("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120).read().decode("utf-8","replace")
for term in ["minTemperature", "icon-drier_iocn", "icon-discharging", "icon-icon-phot", "icon-icon-battery"]:
    positions = []
    start = 0
    while True:
        i = app.find(term, start)
        if i < 0: break
        positions.append(i)
        start = i + 1
    print(term, len(positions), positions[:5])

# find co-occurrence window
i = app.find("minTemperature")
window = app[i:i+5000]
for term in ["icon-", "drier", "discharg", "phot", "battery", "temp"]:
    if term in window:
        j = window.find(term)
        print("in window", term, j, window[max(0,j-40):j+80].replace("\n"," "))
