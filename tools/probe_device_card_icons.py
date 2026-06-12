#!/usr/bin/env python3
"""Find device summary card icon mapping in Fox Cloud bundles."""
import re
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
app_m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index)
app_url = "https://www.foxesscloud.com" + app_m.group(1)
print("app", app_url)
app = fetch(app_url)

# Find deviceDetails chunk
for pat in [
    r"deviceDetails[^\"']{0,80}\.js",
    r"8441\.[^\"']+\.js",
    r"summaryList",
    r"pvPower.*?icon",
    r"minTemperature",
    r"batSoc",
]:
    ms = list(re.finditer(pat, app, re.I))
    print(f"\n=== {pat} ({len(ms)} hits) ===")
    for m in ms[:5]:
        start = max(0, m.start() - 120)
        end = min(len(app), m.end() + 300)
        print(app[start:end])
        print("---")

# Search all chunk references
chunks = sorted(set(re.findall(r'"(\d+\.[a-f0-9]+\.js)"', app)))
print(f"\n{len(chunks)} chunks referenced")

keywords = ["pvPower", "batSoc", "minTemperature", "discharging", "summaryList", "realTimeCurve", "deviceDetails"]
for chunk in chunks:
    if not any(k.lower() in chunk.lower() for k in ["8441", "device"]):
        # only fetch chunks that might be device related - search app for chunk hash near deviceDetails
        pass

# Find chunk id near deviceDetails route
for m in re.finditer(r"deviceDetails[^\]]{0,200}", app):
    print("\nROUTE:", m.group(0)[:200])

# brute: search lazy import paths containing device
for m in re.finditer(r'"(8441\.[^"]+\.js)"', app):
    chunk = m.group(1)
    url = f"https://www.foxesscloud.com/v2/assets/js/{chunk}"
    print("\nfetch chunk", url)
    try:
        js = fetch(url)
    except Exception as e:
        print("fail", e)
        continue
    for kw in keywords:
        if kw in js:
            print(f"  contains {kw}")
            for mm in re.finditer(re.escape(kw) + r".{0,500}", js):
                print("   ", mm.group(0)[:400])
                break
    # icon refs near card config
    for mm in re.finditer(r"icon:[^,]{0,80}", js):
        s = mm.group(0)
        if any(x in s for x in ["phot", "battery", "discharg", "drier", "minSoc", "temp", "Soc"]):
            print("  ", s)
