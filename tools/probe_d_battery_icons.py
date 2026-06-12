#!/usr/bin/env python3
"""Probe Fox Cloud device summary icon mapping (icon-d-battery1..4)."""
import re
import urllib.request


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")


def extract_symbol(app: str, icon_id: str) -> str | None:
    m = re.search(rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'', app)
    if not m:
        return None
    raw = m.group(1).replace("\\n", "\n")
    raw = re.sub(r"<symbol([^>]*)>", r"<svg\1>", raw, count=1)
    raw = raw.replace("</symbol>", "</svg>")
    if 'xmlns="http://www.w3.org/2000/svg"' not in raw:
        raw = raw.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return raw


index = fetch("https://www.foxesscloud.com/v2/")
rt_m = re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index)
rt = fetch("https://www.foxesscloud.com" + rt_m.group(1))
h = re.search(r'8441:"([a-f0-9]+)"', rt).group(1)
chunk_url = f"https://www.foxesscloud.com/v2/assets/js/8441.{h}.js"
js = fetch(chunk_url)
print("chunk", chunk_url, "len", len(js))

for icon in [f"icon-d-battery{i}" for i in range(1, 8)]:
    if icon not in js:
        print(icon, "NOT in chunk")
        continue
    for m in re.finditer(re.escape(icon), js):
        start = max(0, m.start() - 250)
        end = min(len(js), m.end() + 250)
        print(f"\n=== {icon} ===")
        print(js[start:end])
        break

app_m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index)
app = fetch("https://www.foxesscloud.com" + app_m.group(1))
print("\n--- extract SVG sizes ---")
for icon in [f"icon-d-battery{i}" for i in range(1, 5)]:
    svg = extract_symbol(app, icon)
    print(icon, "OK" if svg else "MISSING", len(svg or ""))
