"""Format identity values from foxess_modbus entity states."""

from __future__ import annotations

import re

_PACK_TOKEN_RE = re.compile(r"^\d\.\d{3}$")
_LEGACY_VERSION_RE = re.compile(r"^(\d+)\.(\d{2})$")
_INTEGER_RE = re.compile(r"^\d+$")


def format_evo_pack_version(raw: str | None) -> str | None:
    """Decode EVO BMS pack version registers (37033–37036).

    Fox Cloud shows these as Version_BCU (e.g. 0x1004 → 1.004). Older
    foxess_modbus builds used ``value // 100`` formatting (1004 → 10.04);
    some reads also arrive as decimal digits that are hex tokens (1004 → 0x1004).
    """
    if raw in (None, "", "unavailable", "unknown"):
        return None
    text = str(raw).strip()
    if _PACK_TOKEN_RE.fullmatch(text):
        return text
    if _INTEGER_RE.fullmatch(text):
        return _decode_pack_token(int(text)) or text
    legacy = _LEGACY_VERSION_RE.fullmatch(text)
    if legacy:
        combined = int(legacy.group(1)) * 100 + int(legacy.group(2))
        decoded = _decode_pack_token(combined)
        if decoded:
            return decoded
        if 1000 <= combined < 10000:
            try:
                token = int(str(combined), 16)
            except ValueError:
                return text
            decoded = _decode_pack_token(token)
            if decoded:
                return decoded
    return text


def _decode_pack_token(value: int) -> str | None:
    if value < 0x1000:
        return None
    major = (value >> 12) & 0xF
    minor = value & 0xFFF
    if major < 1 or major > 4:
        return None
    return f"{major}.{minor:03d}"
