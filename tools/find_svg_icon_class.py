#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

app = fetch("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js")

# svg-icon component usage with our icon ids
for iid in ["icon-phot", "icon-battery", "icon-discharge", "minSoc", "drier", "discharging"]:
    pat = f'icon-class:"{iid}"'
    if pat in app:
        i = app.find(pat)
        print(f"\n=== {pat} ===")
        print(app[max(0,i-200):i+400])
    pat2 = f'"icon-class":"{iid}"'
    if pat2 in app:
        i = app.find(pat2)
        print(f"\n=== {pat2} ===")
        print(app[max(0,i-200):i+400])

# search without icon- prefix
for iid in ["icon-icon-phot", "icon-icon-battery", "icon-icon-discharge", "icon-minSoc", "icon-drier_iocn"]:
    short = iid.replace("icon-", "", 1) if iid.startswith("icon-") else iid
    for name in [iid, short, iid.replace("icon-icon-", "icon-")]:
        for pat in [f'icon-class:"{name}"', f"iconClass:\"{name}\""]:
            if pat in app:
                i = app.find(pat)
                print(f"\n=== {pat} ===")
                print(app[max(0,i-250):i+450])

# Real device card list - search pvPower as object key in JS (not i18n)
for m in re.finditer(r"pvPower:", app):
    i = m.start()
    sn = app[i - 50 : i + 200]
    if "PV Power" in sn or "icon" in sn or "svg" in sn or "class" in sn:
        print("\npvPower key:", sn)

# Search for card config with label keys
for m in re.finditer(r"\{label:[^}]{0,80}icon[^}]{0,120}\}", app):
    s = m.group(0)
    if any(k in s for k in ["pv", "bat", "Soc", "Temp", "Discharg", "Power"]):
        print("\nOBJ", s[:250])

# Try CSS for device realtime cards
css = fetch("https://www.foxesscloud.com/v2/assets/css/app.8a3957c4.css")
for term in ["deviceDetail", "realTime", "summary", "dataCard", "topCard", "icon-phot", "minSoc"]:
    if term.lower() in css.lower():
        print("css has", term)
        idx = css.lower().find(term.lower())
        print(css[max(0,idx-100):idx+300][:350])
