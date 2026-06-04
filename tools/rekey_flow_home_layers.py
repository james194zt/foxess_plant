#!/usr/bin/env python3
"""Black-matte flow_home_* only. Do not re-bake bg_scene here — use bake_flow_bg_scenes.py or restore_bg_scenes.py."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from key_flow_home_sky import CANVAS, FLOW_THEMES, remove_black_matte_only

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"


def rekey_home(theme: str) -> None:
    path = WWW / f"flow_home_{theme}.png"
    raw = Image.open(path).convert("RGBA")
    if raw.size != CANVAS:
        raw = raw.resize(CANVAS, Image.Resampling.LANCZOS)
    out = remove_black_matte_only(raw)
    out.save(path, optimize=True)
    print(f"rekeyed {path.name} ({path.stat().st_size} bytes)")


def main() -> None:
    for theme in FLOW_THEMES:
        rekey_home(theme)


if __name__ == "__main__":
    main()
