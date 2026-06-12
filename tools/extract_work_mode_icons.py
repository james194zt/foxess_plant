#!/usr/bin/env python3
"""Extract Fox Cloud work-mode SVG icons and emit a JS const for the panel."""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "work_mode_icons"
APP_URL = "http://www.w3.org/2000/svg"

ICON_IDS = {
    "selfUse": "icon-workMode1",
    "feedInPriority": "icon-workMode2",
    "backUp": "icon-workMode3",
    "peakShaving": "icon-peakShaving",
    "forceCharge": "icon-icon-charge",
    "forceDischarge": "icon-icon-discharge",
}


def fetch_app() -> str:
    return urllib.request.urlopen(
        "https://www.foxesscloud.com/v2/assets/js/app.7ad0e083.js", timeout=120
    ).read().decode("utf-8", "replace")


def extract_symbol(app: str, icon_id: str) -> str | None:
    needle = f'id:"{icon_id}"'
    idx = app.find(needle)
    if idx < 0:
        return None
    content_match = re.search(
        r"content:'(<symbol[\s\S]*?</symbol>)'",
        app[idx : idx + 12000],
    )
    if not content_match:
        content_match = re.search(
            r'content:"(<symbol[\s\S]*?</symbol>)"',
            app[idx : idx + 12000],
        )
    if not content_match:
        return None
    raw = content_match.group(1).replace("\\n", "\n").replace('\\"', '"')
    return raw


def symbol_to_inline_svg(symbol: str) -> str:
    vb = re.search(r'viewBox="([^"]+)"', symbol)
    view_box = vb.group(1) if vb else "0 0 48 48"
    inner = re.sub(r"<symbol[^>]*>", "", symbol, count=1).replace("</symbol>", "")
    inner = re.sub(r"\bid=\"icon-[^_\"]+_", 'id="', inner)
    inner = re.sub(r"url\(#icon-[^_\"]+_", "url(#", inner)
    inner = re.sub(r'filter="url\(#icon-[^_\"]+_', 'filter="url(#', inner)
    return (
        f'<svg xmlns="{APP_URL}" viewBox="{view_box}" fill="none">{inner}</svg>'
    )


def minify_svg(svg: str) -> str:
    svg = re.sub(r">\s+<", "><", svg.strip())
    svg = re.sub(r"\s+", " ", svg)
    return svg.replace('"', '\\"')


def main() -> None:
    app = fetch_app()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    icons: dict[str, str] = {}

    for key, icon_id in ICON_IDS.items():
        sym = extract_symbol(app, icon_id)
        if not sym:
            print(f"MISSING: {key} ({icon_id})")
            continue
        inline = symbol_to_inline_svg(sym)
        (OUT_DIR / f"{key}.svg").write_text(inline, encoding="utf-8")
        icons[key] = minify_svg(inline)
        print(f"ok {key} ({len(inline)} bytes)")

    pairs = ", ".join(f'"{k}": "{v}"' for k, v in icons.items())
    const_js = f"const FOX_WORK_MODE_ICONS = {{{pairs}}};"
    (ROOT / "fox_work_mode_icons.const.js").write_text(const_js + "\n", encoding="utf-8")
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(list(icons.keys()), indent=2), encoding="utf-8"
    )
    print(f"wrote {ROOT / 'fox_work_mode_icons.const.js'}")


if __name__ == "__main__":
    main()
