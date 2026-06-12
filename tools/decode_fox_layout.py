#!/usr/bin/env python3
"""Decode Fox app binary AXML layout to readable XML."""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

LAYOUT = Path(
    r"C:\Users\James\Downloads\foxcloud2-0-2-2-12\com.fox.foxapp.two\res\layout\fragment_plant_hybrid_flow.xml"
)


def decode_with_apkutils(path: Path) -> str | None:
    try:
        from androguard.core.bytecodes.AXML import AXML  # type: ignore

        return AXML(path.read_bytes()).get_xml().decode("utf-8", errors="replace")
    except Exception:
        return None


def decode_with_axmlparserpy(path: Path) -> str | None:
    try:
        from axmlparserpy import axmlprinter  # type: ignore

        return axmlprinter.AXMLPrinter(path.read_bytes()).get_xml()
    except Exception:
        return None


def strings_from_binary(path: Path) -> list[str]:
    data = path.read_bytes()
    return re.findall(rb"[\x20-\x7e]{4,}", data)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else LAYOUT
    if not path.is_file():
        print(f"missing {path}")
        return 1

    for fn in (decode_with_apkutils, decode_with_axmlparserpy):
        xml = fn(path)
        if xml:
            print(xml)
            return 0

    print("=== Could not decode AXML; printable strings in layout binary ===")
    for s in strings_from_binary(path):
        t = s.decode("ascii", errors="ignore")
        if any(
            k in t.lower()
            for k in (
                "flow",
                "home",
                "pv",
                "aio",
                "image",
                "view",
                "layout",
                "bg",
                "plant",
                "hybrid",
            )
        ):
            print(t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
