#!/usr/bin/env python3
import logging
import re
from pathlib import Path

logging.disable(logging.CRITICAL)

from androguard.core.axml import ARSCParser, AXMLPrinter

ARSC = Path(
    "/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/resources.arsc"
)
LAYOUT = Path(
    "/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/res/layout/fragment_plant_hybrid_flow.xml"
)

KEY_IDS = [
    0x7F0F00A1,
    0x7F0F00B1,
    0x7F0F00FB,
    0x7F0F009D,
    0x7F0700A0,
]


def main() -> None:
    arsc = ARSCParser(ARSC.read_bytes())
    print("=== key layout resource IDs ===")
    for rid in KEY_IDS:
        try:
            name = arsc.get_resource_xml_name(rid)
        except Exception as e:
            name = f"ERR {e}"
        print(f"  0x{rid:08X} -> {name}")

    xml = AXMLPrinter(LAYOUT.read_bytes()).get_xml().decode("utf-8", errors="replace")
    refs = sorted(set(int(m[1:], 16) for m in re.findall(r"@7F[0-9A-F]{8}", xml, flags=re.I)))
    print("\n=== flow-related refs in hybrid flow layout ===")
    for rid in refs:
        try:
            name = arsc.get_resource_xml_name(rid)
        except Exception:
            continue
        if "flow" in name.lower() or name.startswith("flow_"):
            print(f"  0x{rid:08X} -> {name}")


if __name__ == "__main__":
    main()
