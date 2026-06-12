#!/usr/bin/env python3
"""Extract Fox Cloud analysis supply/usage SVG icons from public app.js bundle."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

APP_URL = "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js"
OUT = Path(__file__).resolve().parents[1] / "custom_components/foxess_plant/www/fox-analysis-icons.json"

ICON_IDS = {
    "imported": "icon-e_grid_import",
    "pv_produced": "icon-icon-phot",
    "discharged": "icon-icon-discharge",
    "exported": "icon-e_grid_export",
    "consumed": "icon-icon-load",
    "charged": "icon-icon-battery",
}


def extract_symbol(app: str, icon_id: str) -> str | None:
    m = re.search(rf'id:"{re.escape(icon_id)}"[^}}]*content:\'([^\']+)\'', app)
    if not m:
        return None
    raw = m.group(1).replace("\\n", "\n")
    # symbol -> inline svg for 32px display
    raw = re.sub(r"<symbol([^>]*)>", r"<svg\1>", raw, count=1)
    raw = raw.replace("</symbol>", "</svg>")
    raw = re.sub(r'\s+xmlns="http://www.w3.org/2000/svg"', "", raw, count=1)
    if 'xmlns="http://www.w3.org/2000/svg"' not in raw:
        raw = raw.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return raw


def main() -> None:
    app = urllib.request.urlopen(APP_URL, timeout=120).read().decode("utf-8", "replace")
    icons: dict[str, str] = {}
    missing: list[str] = []
    for key, icon_id in ICON_IDS.items():
        svg = extract_symbol(app, icon_id)
        if svg:
            icons[key] = svg
        else:
            missing.append(icon_id)
    OUT.write_text(json.dumps({"icons": icons, "missing": missing}, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(icons)} icons, missing={missing})")


if __name__ == "__main__":
    main()
