#!/usr/bin/env python3
"""Extract Fox Cloud device summary + realtime icons from live app.js bundle."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "custom_components/foxess_plant/www/fox-device-icons.json"

# Device summary cards use icon-d-battery1..4 (40×40 circle badges).
# Fox maps by metric semantics (not DOM index order): battery, bolt, thermometer, generation.
ICON_CANDIDATES = {
    "battery_soc": ["icon-d-battery1"],
    "discharging": ["icon-d-battery2"],
    "temperature": ["icon-d-battery3"],
    "pv_power": ["icon-d-battery4"],
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", "replace")


def find_app_js_url(index_html: str) -> str:
    m = re.search(r'src="(/v2/assets/js/app\.[^"]+\.js)"', index_html)
    if not m:
        raise SystemExit("app.js not found in index")
    return "https://www.foxesscloud.com" + m.group(1)


def extract_symbol(app: str, icon_id: str) -> str | None:
    m = re.search(rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'', app)
    if not m:
        return None
    raw = m.group(1).replace("\\n", "\n")
    raw = re.sub(r"<symbol([^>]*)>", r"<svg\1>", raw, count=1)
    raw = raw.replace("</symbol>", "</svg>")
    raw = re.sub(r'\s+xmlns="http://www.w3.org/2000/svg"', "", raw, count=1)
    if 'xmlns="http://www.w3.org/2000/svg"' not in raw:
        raw = raw.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return raw


def main() -> None:
    index = fetch("https://www.foxesscloud.com/v2/")
    app_url = find_app_js_url(index)
    print("fetching", app_url)
    app = fetch(app_url)
    all_ids = sorted(set(re.findall(r'id:"(icon-[^"]+)"', app)))
    print(f"found {len(all_ids)} icon ids")

    icons: dict[str, str] = {}
    missing: list[str] = []
    used: dict[str, str] = {}

    for key, candidates in ICON_CANDIDATES.items():
        svg = None
        pick = None
        for cid in candidates:
            svg = extract_symbol(app, cid)
            if svg:
                pick = cid
                break
        if not svg:
            patterns = {
                "pv_power": r"icon-d-battery1",
                "battery_soc": r"icon-d-battery2",
                "discharging": r"icon-d-battery3",
                "temperature": r"icon-d-battery4",
            }
            pat = patterns[key]
            for cid in all_ids:
                if not re.search(pat, cid, re.I):
                    continue
                if key == "battery_soc" and re.search(r"discharg", cid, re.I):
                    continue
                svg = extract_symbol(app, cid)
                if svg:
                    pick = cid
                    break
        if svg:
            icons[key] = svg
            used[key] = pick or ""
            print(f"  {key}: {pick}")
        else:
            missing.append(key)
            print(f"  {key}: MISSING")

    review = [
        i
        for i in all_ids
        if re.search(r"phot|pv|battery|discharg|temp|therm|soc|power|device", i, re.I)
    ]
    OUT.write_text(
        json.dumps({"icons": icons, "missing": missing, "used": used, "reviewIds": review}, indent=2),
        encoding="utf-8",
    )
    print("wrote", OUT)


if __name__ == "__main__":
    main()
