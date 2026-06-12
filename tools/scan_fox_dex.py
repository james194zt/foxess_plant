#!/usr/bin/env python3
"""Find flow_home / PlantFragmentHybridFlow references in Fox APK dex."""
import logging
import re
from pathlib import Path

logging.disable(logging.CRITICAL)

APK_DIR = Path("/mnt/c/Users/James/Downloads/foxcloud2-0-2-2-12/com.fox.foxapp.two")
PATTERNS = (
    "flow_home",
    "flow_home_bg",
    "flow_pv",
    "flow_aio",
    "PlantFragmentHybridFlow",
    "binding_2",
    "iv_0736",
    "071D",
)


def main() -> None:
    for dex in sorted(APK_DIR.glob("*.dex")):
        data = dex.read_bytes()
        text = data.decode("latin-1", errors="ignore")
        hits = []
        for pat in PATTERNS:
            if pat in text:
                hits.append(pat)
        if hits:
            print(f"{dex.name}: {', '.join(hits)}")
        for pat in ("flow_home_day_light", "flow_home_bg_day_light", "setFlowTheme"):
            idx = text.find(pat)
            if idx >= 0:
                snippet = text[max(0, idx - 40) : idx + len(pat) + 60]
                snippet = re.sub(r"[^\x20-\x7e]", ".", snippet)
                print(f"  [{pat}] ...{snippet}...")


if __name__ == "__main__":
    main()
