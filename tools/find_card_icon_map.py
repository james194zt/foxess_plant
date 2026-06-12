#!/usr/bin/env python3
import re
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
app = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index).group(1))
rt = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index).group(1))
chunks = dict(re.findall(r'(\d+):"([a-f0-9]+)"', rt))

# Search all chunks for icon-d-battery + metric keys together
for cid, h in chunks.items():
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        continue
    if "icon-d-battery1" not in js:
        continue
    if not any(k in js for k in ["pvPower", "batSoc", "DischargePower", "minTemperature", "realTime"]):
        # skip pure svg registration chunks
        if js.count("icon-d-battery1") <= 3 and "content:'" in js:
            continue
    print(f"\nCHUNK {cid} len={len(js)}")
    for pat in [
        r"icon-d-battery[1-4][^,]{0,80}",
        r"pvPower[^,]{0,120}",
        r"batSoc[^,]{0,120}",
        r"DischargePower[^,]{0,120}",
        r"minTemperature[^,]{0,120}",
        r"topLine[^,]{0,80}",
        r"cardColor[^,]{0,80}",
        r"bgStyle[^,]{0,120}",
        r"linear-gradient[^)]{0,200}",
    ]:
        m = re.search(pat, js)
        if m:
            print(" ", m.group(0)[:200])

# Search app for card list array
for m in re.finditer(r"\{[^{}]{0,80}icon-d-battery[1-4][^{}]{0,300}\}", app):
    s = m.group(0)
    if any(k in s for k in ["pv", "bat", "Soc", "temp", "Discharge", "power", "key", "type"]):
        print("\nAPP OBJ", s[:400])
