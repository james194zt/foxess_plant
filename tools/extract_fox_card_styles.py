#!/usr/bin/env python3
"""Extract Fox device summary card colors/gradients from app CSS + JS."""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "custom_components/foxess_plant/www/fox-device-summary-styles.json"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.foxesscloud.com/v2/"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")


index = fetch("https://www.foxesscloud.com/v2/")
css_url = "https://www.foxesscloud.com" + re.search(r'href="(/v2/assets/css/app\.[^"]+\.css)"', index).group(1)
css = fetch(css_url)
app = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index).group(1))

# CSS custom properties related to cards
vars_found = {}
for m in re.finditer(r"--([a-zA-Z0-9_-]+)\s*:\s*([^;}{]+)", css):
    name, val = m.group(1), m.group(1)
    val = m.group(2).strip()
    if any(k in name.lower() for k in ["card", "device", "real", "data", "summary", "top", "bg", "border", "gradient"]):
        vars_found[f"--{name}"] = val

# search vue scoped css modules in chunks for top border / gradient on cards
rt = fetch("https://www.foxesscloud.com" + re.search(r'src="(/v2/assets/js/runtime\.[^"]+\.js)"', index).group(1))
chunks = dict(re.findall(r'(\d+):"([a-f0-9]+)"', rt))

style_snippets = []
for cid, h in chunks.items():
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        continue
    if len(js) < 8000 or js.startswith("<!"):
        continue
    if not any(t in js for t in ["linear-gradient", "border-top", "topLine", "topColor", "cardBg", "dataCard", "realTime"]):
        continue
    for m in re.finditer(r"linear-gradient\([^)]+\)", js):
        g = m.group(0)
        if any(c in g for c in ["08979C", "894BFC", "03BD9A", "699BFF", "FA8C16", "19D4DE", "69B1FF"]):
            style_snippets.append({"chunk": cid, "gradient": g[:300]})
    for m in re.finditer(r"(?:topLine|topColor|borderTop|cardBg|bgColor|lineColor)\s*:\s*\"([^\"]+)\"", js):
        style_snippets.append({"chunk": cid, "prop": m.group(0)[:200]})

# Fox chart palette from energy chunks (authoritative accent colors)
palette = {}
for m in re.finditer(r'(pvPower|batSoc|SoC|batDischargePower|minTemperature|loadsPower):"(#[0-9A-Fa-f]{3,8})"', app):
    palette[m.group(1)] = m.group(2)
for cid, h in chunks.items():
    url = f"https://www.foxesscloud.com/v2/assets/js/{cid}.{h}.js"
    try:
        js = fetch(url)
    except Exception:
        continue
    for m in re.finditer(r'(pvPower|SoC|batDischargePower|loadsPower):"(#[0-9A-Fa-f]{3,8})"', js):
        palette[m.group(1)] = m.group(2)

# Known Fox device summary card accents (from chart palette + icon-d-device fills)
cards = {
    "pv_power": {
        "icon": "icon-d-battery4",
        "accent": palette.get("pvPower", "#08979C"),
        "icon_alt": "icon-icon-phot",
    },
    "battery_soc": {
        "icon": "icon-d-battery1",
        "accent": "#894BFC",
    },
    "discharging": {
        "icon": "icon-d-battery2",
        "accent": palette.get("batDischargePower", "#69B1FF"),
    },
    "temperature": {
        "icon": "icon-d-battery3",
        "accent": palette.get("loadsPower", "#FA8C16"),
    },
}

# Build card surface styles approximating Fox (light tint + top gradient line)
for key, meta in cards.items():
    accent = meta["accent"]
    meta["border_top"] = accent
    meta["background"] = f"linear-gradient(180deg, {accent}1A 0%, {accent}08 42%, transparent 100%)"
    meta["surface"] = f"linear-gradient(145deg, {accent}14 0%, rgba(255,255,255,0.02) 55%, transparent 100%)"

payload = {
    "cards": cards,
    "palette": palette,
    "css_vars_sample": dict(list(vars_found.items())[:40]),
    "style_snippets": style_snippets[:20],
}
OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print("wrote", OUT)
print(json.dumps(cards, indent=2))
