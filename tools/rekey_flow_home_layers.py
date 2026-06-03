#!/usr/bin/env python3
"""Re-key flow_home_* and flow_home_bg_* with luminance alpha (Fox-style ground fade)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from key_flow_home_sky import CANVAS, FLOW_THEMES, process_home_layer

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"


def rekey_home(theme: str) -> None:
    path = WWW / f"flow_home_{theme}.png"
    raw = Image.open(path).convert("RGBA")
    if raw.size != CANVAS:
        raw = raw.resize(CANVAS, Image.Resampling.LANCZOS)
    out = process_home_layer(raw)
    out.save(path, optimize=True)
    print(f"rekeyed {path.name} ({path.stat().st_size} bytes)")


def main() -> None:
    for theme in FLOW_THEMES:
        rekey_home(theme)


if __name__ == "__main__":
    main()
