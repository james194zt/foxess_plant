#!/usr/bin/env python3
import re
import urllib.request

app = urllib.request.urlopen(
    "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
).read().decode("utf-8", "replace")

# webpack chunk filename map: {8441:"abc123",...}
m = re.search(r"\{(\d+:\"[a-f0-9]+\"(?:,\d+:\"[a-f0-9]+\")*)\}", app)
if m:
    mapping = "{" + m.group(1) + "}"
    pairs = re.findall(r"(\d+):\"([a-f0-9]+)\"", mapping)
    chunk_map = dict(pairs)
    print("chunks", len(chunk_map))
    h = chunk_map.get("8441")
    if h:
        url = f"https://www.foxesscloud.com/v2/assets/js/8441.{h}.js"
        print("fetch", url)
        chunk = urllib.request.urlopen(url, timeout=120).read().decode("utf-8", "replace")
        for key in ["minTemperature", "pvPower", "batSoc", "discharging", "icon-icon", "summaryList", "cardList"]:
            if key in chunk:
                i = chunk.find(key)
                print("\n===", key, "===")
                print(chunk[max(0, i - 150) : i + 350].replace("\n", " ")[:500])
else:
    print("no chunk map")
