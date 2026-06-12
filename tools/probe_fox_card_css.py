#!/usr/bin/env python3
import re
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")

index = fetch("https://www.foxesscloud.com/v2/")
css_url = "https://www.foxesscloud.com" + re.search(r'href="(/v2/assets/css/app\.[^"]+\.css)"', index).group(1)
css = fetch(css_url)
print("css", css_url)

colors = ["19D4DE", "894BFC", "03BD9A", "699BFF", "FA8C16", "EB6D48", "52C41A"]
for c in colors:
    if c.lower() in css.lower():
        print("color", c, "present")

# scoped module classes from device chunks
rt = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index).group(1))
chunks = dict(re.findall(r'(\d+):"([a-f0-9]+)"', rt))
for cid, h in chunks.items():
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        continue
    if len(js) < 8000 or js.startswith("<!"):
        continue
    if not any(k in js for k in ["topLineColor", "cardBg", "cardStyle", "summary", "realTime", "icon-d-battery"]):
        continue
    if "icon-d-battery1" in js and ("pvPower" in js or "batSoc" in js or "key:" in js):
        print("\nchunk", cid, len(js))
        for m in re.finditer(r"key:\"[^\"]+\"[^}]{0,250}", js):
            s = m.group(0)
            if "icon" in s or "color" in s or "bg" in s.lower() or "line" in s.lower():
                print(" ", s[:220])

# CSS rules with gradient + border-top
for m in re.finditer(r"[^{}]{0,40}\{[^}]*(?:linear-gradient|border-top)[^}]{0,200}\}", css):
    s = m.group(0)
    if any(c.lower() in s.lower() for c in colors):
        print("\nCSS rule:", s[:300])
