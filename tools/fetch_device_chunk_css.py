#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(
        u,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.foxesscloud.com/v2/plants/deviceDetails?category=aio",
            "Accept": "*/*",
        },
    )
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

rt = fetch("https://www.foxesscloud.com/v2/assets/js/runtime.d2b21310.js")
hashes = re.findall(r'8441:"([a-f0-9]+)"', rt)
print("8441 hashes", hashes)

for h in hashes:
    url = f"https://www.foxesscloud.com/v2/assets/js/8441.{h}.js"
    js = fetch(url)
    print(url, "is_html", js.startswith("<!"), "len", len(js))
    if not js.startswith("<!") and len(js) > 10000:
        for kw in ["pvPower", "icon", "svg-icon", "minSoc", "DischargePower"]:
            if kw in js:
                print(" ", kw, "found")

css = fetch("https://www.foxesscloud.com/v2/assets/css/app.8a3957c4.css")
# extract rules with device/real/card keywords
for m in re.finditer(r"\.[a-zA-Z_-]*(?:device|real|card|data|summary)[a-zA-Z0-9_-]*\{[^}]+\}", css):
    s = m.group(0)
    if len(s) < 400:
        print("\nCSS:", s[:350])

# broader search in css
for term in ["realTime", "deviceDetail", "topData", "dataList", "iconBox", "cardItem"]:
    i = css.find(term)
    if i >= 0:
        print(f"\nCSS {term}:", css[max(0, i - 20) : i + 200][:220])
