#!/usr/bin/env python3
import re
import urllib.request

APP = "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js"
js = urllib.request.urlopen(APP, timeout=60).read().decode("utf-8", "replace")
print("app len", len(js))
for pat in ["plants-analysis", "2146a659", "eenery_stat", "Imported", "svg-block", "flow_l"]:
    print(pat, js.count(pat))

for m in re.finditer(r"plants-analysis[^\"']{0,80}", js):
    print("ref:", m.group(0)[:120])

# lazy chunk filenames
for m in re.finditer(r"(\d+)\s*:\s*\"([a-f0-9]+)\"", js[:500000]):
    pass

runtime = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/runtime.d2b21310.js", timeout=60
).read().decode("utf-8", "replace")
for name in ["plants-analysis", "2146a659", "eenery"]:
    print("runtime", name, runtime.count(name))

# try direct chunk paths from css hash pattern
for chunk in [
    "plants-analysis.20d73d46.js",
    "8318.a9c37d8a.js",
    "6060.44b18fef.js",
    "4342.512f2032.js",
]:
    url = f"https://www.foxesscloud.com/v2/assets/js/{chunk}"
    try:
        data = urllib.request.urlopen(url, timeout=30).read().decode("utf-8", "replace")
        print(chunk, "len", len(data), "2146a659", data.count("2146a659"))
        if "2146a659" in data or "eenery_stat" in data:
            open(f"/tmp/{chunk}", "w", encoding="utf-8").write(data)
            print("  saved", chunk)
    except Exception as e:
        print(chunk, "fail", e)
