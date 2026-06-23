#!/usr/bin/env python3
"""Re-encode hero banner assets as real PNG (fixes JPEG-in-.png MIME mismatch)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

WWW = Path(__file__).resolve().parents[1] / "custom_components" / "foxess_plant" / "www"
NAMES = ("bg_smart_charge.png", "bg_storm_safe_charging.png")


def main() -> None:
    for name in NAMES:
        path = WWW / name
        img = Image.open(path)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        img.save(path, format="PNG", optimize=True)
        print(f"{name}: {img.size} {img.mode}")


if __name__ == "__main__":
    main()
