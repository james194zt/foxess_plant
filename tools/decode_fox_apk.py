#!/usr/bin/env python3
"""Decode Fox APK layouts and map flow_home_day_light resources."""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

logging.disable(logging.CRITICAL)

APK_RES = Path(
    "/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/res"
)
LAYOUT = APK_RES / "layout/fragment_plant_hybrid_flow.xml"
ARSC = Path(
    "/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/resources.arsc"
)


def decode_layout(path: Path) -> str:
    from androguard.core.axml import AXMLPrinter

    return AXMLPrinter(path.read_bytes()).get_xml().decode("utf-8", errors="replace")


def resolve_id(rid: int) -> str:
    from androguard.core.axml import ARSCParser

    arsc = ARSCParser(ARSC.read_bytes())
    try:
        return arsc.get_resource_xml_name(rid)
    except Exception:
        return f"0x{rid:08X}"


def main() -> int:
    if not LAYOUT.is_file():
        print(f"Missing {LAYOUT}")
        return 1

    xml = decode_layout(LAYOUT)
    out_path = Path(__file__).resolve().parent / "fox_fragment_plant_hybrid_flow.decoded.xml"
    out_path.write_text(xml, encoding="utf-8")
    print(f"Wrote {out_path}")

    if ARSC.is_file():
        print("\n=== Key scene resource IDs ===")
        for rid in (0x7F0F009D, 0x7F0F00A1, 0x7F0F00B1):
            print(f"  {resolve_id(rid)}")

    # Summarise scene layer views
    print("\n=== Scene-related views in layout ===")
    for m in re.finditer(
        r'<(ImageView|com\.fox\.foxcloud\.ui\.view\.widget\.flow\.[^"]+)[^>]*android:tag="([^"]+)"[^>]*>',
        xml,
    ):
        print(f"  {m.group(1)}  tag={m.group(2)}")
    for m in re.finditer(
        r'android:tag="(binding_\d+)"',
        xml,
    ):
        pass
    tags = sorted(set(re.findall(r'android:tag="(binding_\d+)"', xml)))
    print(f"  Data-binding tags: {', '.join(tags)}")

    flow_views = re.findall(
        r"<com\.fox\.foxcloud\.ui\.view\.widget\.flow\.LineFlow[^>]+>",
        xml,
    )
    print(f"  LineFlow widgets: {len(flow_views)}")

    # binding -> likely ImageViews with ids
    for block in re.split(r"(<ImageView\b)", xml)[1:]:
        if "binding_" not in block:
            continue
        tag = re.search(r'android:tag="(binding_\d+)"', block)
        cid = re.search(r'android:id="@\+id/([^"]+)"', block)
        if tag:
            extra = f" id={cid.group(1)}" if cid else ""
            print(f"  ImageView tag={tag.group(1)}{extra}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
