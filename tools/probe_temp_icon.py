#!/usr/bin/env python3
import re
import urllib.request

def fetch(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    return urllib.request.urlopen(r, timeout=120).read().decode("utf-8", "replace")

app = fetch("https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js")

print("SVG modules:")
for m in re.finditer(r'"\./([^"]+\.svg)":(\d+)', app):
    name = m.group(1)
    if re.search(r"temp|therm|drier|dr-|min|soc|phot|battery|discharg|charge|device", name, re.I):
        print(f"  {name} -> {m.group(2)}")

def extract(app_text, icon_id):
    m = re.search(rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'', app_text)
    if not m:
        return None
    raw = m.group(1).replace("\\n", "\n")
    raw = re.sub(r"<symbol([^>]*)>", r"<svg\1>", raw, count=1).replace("</symbol>", "</svg>")
    if 'xmlns="http://www.w3.org/2000/svg"' not in raw:
        raw = raw.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return raw

# dr-iocn module 1479
m = re.search(r"1479:function\(e,a,t\)", app)
if m:
    sn = app[m.start() : m.start() + 800]
    idm = re.search(r'id:"([^"]+)"', sn)
    print("\n1479 id", idm.group(1) if idm else "?")
    print(sn[:500])

for iid in ["icon-dr-iocn", "icon-drier_iocn", "icon-minSoc"]:
    svg = extract(app, iid)
    if svg:
        print(f"\n{iid} viewBox check, len={len(svg)}")
        # describe visually from paths
        if "1CA157" in svg or "therm" in svg.lower():
            print("  has green thermometer colors")

# Search minTemperature near svg require in app - look within 5000 chars of minTemperature i18n key for icon references  
i = app.find('minTemperature:"Min. Battery Temperature"')
chunk = app[i : i + 8000]
for term in ["icon", "svg", "77286", "68177", "70086", "45075", "95672", "51002", "icon-phot", "minSoc", "drier"]:
    if term in chunk:
        print(f"near minTemperature i18n: has {term}")

# Search backwards from minTemperature for component definition
chunk2 = app[max(0, i - 15000) : i + 2000]
for term in ["icon-minSoc", "icon-drier", "icon-phot", "icon-discharge", "icon-battery", "77286", "45075", "95672"]:
    pos = chunk2.rfind(term)
    if pos >= 0:
        print(f"before minTemperature: {term} at offset {pos - len(chunk2)}")

# brute: find minTemperature key in data object (not i18n)
for m in re.finditer(r"minTemperature", app):
    i = m.start()
    if app[i:i+30].startswith('minTemperature:"Min.'):
        continue
    ctx = app[max(0,i-300):i+500]
    if "icon" in ctx or "svg" in ctx or "77286" in ctx or "45075" in ctx or "95672" in ctx:
        print("\nDATA minTemperature:")
        print(ctx[:700])
