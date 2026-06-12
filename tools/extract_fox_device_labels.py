#!/usr/bin/env python3
import re, urllib.request
app = urllib.request.urlopen("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120).read().decode("utf-8","replace")
keys = [
    "pvInfo","acInfo","epsInfo","loadInfo","gridInfo","batInfo","datalogger",
    "loadLabel","gridLabel","batLabel","nominalLabel","pvPower","batSoc",
    "voltage","current","power","frequency","state","meter","realTimeCurve",
    "feedIn","purchased","discharging","minTemperature","gridStatus",
]
found = {}
for m in re.finditer(r"(\w+Label\d?|\w+Info|\w+Power|\w+Soc|\w+Status):\"([^\"]+)\"", app):
    k, v = m.group(1), m.group(2)
    if any(x in k.lower() for x in ["load","grid","bat","pv","ac","eps","nominal","feed","purch","datalog","meter","temp","discharg","real","curve"]):
        found[k] = v
for k in sorted(found):
    print(f"{k}: {found[k]}")
