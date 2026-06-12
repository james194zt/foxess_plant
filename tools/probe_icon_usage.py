#!/usr/bin/env python3
import re, urllib.request
app = urllib.request.urlopen("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120).read().decode("utf-8","replace")
for cid in ["icon-drier_iocn", "icon-discharging", "icon-icon-phot", "icon-icon-battery", "icon-minSoc"]:
    for m in re.finditer(re.escape(cid), app):
        i = m.start()
        ctx = app[max(0,i-120):i+180].replace("\n"," ")
        if "require" not in ctx and "id:" not in ctx[:30]:
            print("USE", cid, ctx[:260])
            break
