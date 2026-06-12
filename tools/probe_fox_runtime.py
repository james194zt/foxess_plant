#!/usr/bin/env python3
import json
import re
import urllib.request

runtime = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/runtime.d2b21310.js", timeout=60
).read().decode("utf-8", "replace")
# extract chunk mapping
idx = runtime.find("plants-analysis")
print("idx", idx)
print(runtime[idx - 200 : idx + 400])

# find all js asset names in app
app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=60
).read().decode("utf-8", "replace")
chunks = sorted(set(re.findall(r"assets/js/[a-zA-Z0-9_.-]+\.js", app)))
print("chunks in app", len(chunks))
for c in chunks:
    if "analysis" in c.lower() or "8318" in c or "6060" in c:
        print(c)

# parse webpack jsonp chunk mapping from runtime
for m in re.finditer(r'\{"(\d+)":"([a-f0-9]+)"\}', runtime):
    pass

# simpler: find plants-analysis in runtime with hash
m = re.search(r'"plants-analysis"\s*:\s*"([a-f0-9]+)"', runtime)
print("hash match", m.group(1) if m else None)

# try u.j pattern
m = re.search(r'4264:"([a-f0-9]+)"', runtime)
print("4264 hash", m.group(1) if m else None)
if m:
    url = f"https://www.foxesscloud.com/v2/assets/js/4264.{m.group(1)}.js"
    print("url", url)
    data = urllib.request.urlopen(url, timeout=60).read().decode("utf-8", "replace")
    print("chunk len", len(data))
    for pat in ["2146a659", "eenery_stat", "Imported", "svg", "viewBox", "path d", "flow_l", "Discharged", "PV Produced"]:
        print(pat, data.count(pat))
    # extract svg snippets
    for m2 in re.finditer(r"<svg[^>]{0,200}viewBox[^<]{0,2000}</svg>", data):
        print("SVG:", m2.group(0)[:500])
        break
    # inline svg in vue render
    for m2 in re.finditer(r'viewBox=\"0 0 \d+ \d+\"[^$]{0,1500}', data):
        s = m2.group(0)
        if "path" in s:
            print("VB:", s[:800])
            break
