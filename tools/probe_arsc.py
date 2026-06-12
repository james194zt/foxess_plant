#!/usr/bin/env python3
import logging
import os

os.environ["LOGURU_LEVEL"] = "ERROR"
logging.disable(logging.CRITICAL)

from pathlib import Path
from androguard.core.axml import ARSCParser

ARSC = Path(
    "/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two/resources.arsc"
)
arsc = ARSCParser(ARSC.read_bytes())
print([m for m in dir(arsc) if "pack" in m.lower() or "name" in m.lower()])
for pkg in arsc.get_packages_names():
    print("pkg", pkg)
    p = arsc.packages[pkg] if hasattr(arsc, "packages") else None
    if p is None:
        print("  no packages dict")
        continue
    print("  type", type(p).__name__, "methods", [m for m in dir(p) if "res" in m.lower()][:12])
    try:
        cfg = p.get_resolved_res_configs()
        print("  resolved count", len(cfg))
        for k, v in list(cfg.items())[:3]:
            print("   sample", k, v)
    except Exception as e:
        print("  resolved err", e)
