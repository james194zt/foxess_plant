#!/usr/bin/env python3
"""Extract fault code pages from EN-EVO-User-Manual.pdf (pages 54-60)."""

from __future__ import annotations

import sys

try:
    from pypdf import PdfReader
except ImportError:
    print("pip install pypdf", file=sys.stderr)
    raise

PDF = "/mnt/c/Users/James/Downloads/EN-EVO-User-Manual.pdf"
START, END = 53, 65  # pages 54-65

if __name__ == "__main__":
    r = PdfReader(PDF)
    for i in range(START, min(END, len(r.pages))):
        print(f"--- PAGE {i + 1} ---")
        print(r.pages[i].extract_text() or "")
        print()
