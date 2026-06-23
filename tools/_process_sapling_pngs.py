#!/usr/bin/env python3
"""Remove near-black backgrounds from Octopus greener sapling PNGs."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow required: pip install pillow") from exc

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "custom_components" / "foxess_plant" / "www"
FILES = (
    WWW / "octopus_greener_sapling.png",
    WWW / "octopus_greener_sapling_green.png",
)

# Pixels darker than this become transparent (removes baked-in black backdrop).
BLACK_THRESHOLD = 36


def key_out_black(path: Path) -> None:
    img = Image.open(path).convert("RGBA")
    pixels = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if r <= BLACK_THRESHOLD and g <= BLACK_THRESHOLD and b <= BLACK_THRESHOLD:
                pixels[x, y] = (r, g, b, 0)
    img.save(path, format="PNG", optimize=True)
    print(f"Processed {path.name} ({width}x{height})")


def main() -> None:
    for path in FILES:
        if not path.is_file():
            raise SystemExit(f"Missing {path}")
        key_out_black(path)


if __name__ == "__main__":
    main()
