#!/usr/bin/env python3
"""Map Fox APK resource hex IDs to names (WSL)."""
from __future__ import annotations

import logging
import re
from pathlib import Path

logging.disable(logging.CRITICAL)

ARSC = Path(
    "/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/resources.arsc"
)
LAYOUT = Path(
    "/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/res/layout/fragment_plant_hybrid_flow.xml"
)

WANT = {
    "7f0f00a1",
    "7f0f00b1",
    "7f0f00fb",
    "7f0f009d",
    "7f0700a0",
}


def main() -> None:
    from androguard.core.axml import ARSCParser, AXMLPrinter

    arsc = ARSCParser(ARSC.read_bytes())
    rid_to_name: dict[int, str] = {}
    for package_name in arsc.get_packages_names():
        package = arsc.get_packages()[package_name]
        for res_id, entry in package.get_res_configs().items():
            name = res_id[1] if isinstance(res_id, tuple) else str(res_id)
            rid = entry.get_resource_id()
            if rid is not None:
                rid_to_name[rid] = name

    xml = AXMLPrinter(LAYOUT.read_bytes()).get_xml().decode("utf-8", errors="replace")
    refs = sorted(set(re.findall(r"@7F[0-9A-F]{8}", xml, flags=re.I)))
    print("=== flow-related refs in fragment_plant_hybrid_flow ===")
    for ref in refs:
        try:
            rid = int(ref[1:], 16)
        except ValueError:
            continue
        name = rid_to_name.get(rid, "?")
        if "flow" in name.lower() or ref.lower() in WANT:
            print(f"  {ref} -> {name}")

    print("\n=== key drawable/mipmap names ===")
    for name in sorted(rid_to_name.values()):
        if name.startswith("flow_home") or name.startswith("flow_pv") or name.startswith("flow_aio"):
            print(f"  {name}")


if __name__ == "__main__":
    main()
