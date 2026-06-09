#!/usr/bin/env python3
"""Embed fox-device-icons.json into foxess-plant-panel.js as FOX_DEVICE_SUMMARY_ICONS."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "custom_components/foxess_plant/www/fox-device-icons.json"
PANEL = ROOT / "custom_components/foxess_plant/www/foxess-plant-panel.js"
START = "// FOX_DEVICE_SUMMARY_ICONS_START"
END = "// FOX_DEVICE_SUMMARY_ICONS_END"


def main() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    icons = data.get("icons") or {}
    block = START + "\nconst FOX_DEVICE_SUMMARY_ICONS = " + json.dumps(icons, ensure_ascii=False) + ";\n" + END
    text = PANEL.read_text(encoding="utf-8")
    if START in text and END in text:
        pre = text.split(START)[0]
        post = text.split(END)[1]
        text = pre + block + post
    else:
        anchor = "const DEVICE_REALTIME_CHART_SERIES = ["
        idx = text.find(anchor)
        if idx < 0:
            raise SystemExit("anchor not found")
        text = text[:idx] + block + "\n\n" + text[idx:]
    PANEL.write_text(text, encoding="utf-8")
    print(f"embedded {len(icons)} icons into {PANEL}")


if __name__ == "__main__":
    main()
