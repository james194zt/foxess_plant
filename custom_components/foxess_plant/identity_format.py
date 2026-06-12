"""Format identity values from foxess_modbus entity states."""

from __future__ import annotations

import re

_PACK_TOKEN_RE = re.compile(r"^\d\.\d{3}$")
_LEGACY_VERSION_RE = re.compile(r"^(\d+)\.(\d{2})$")
_INTEGER_RE = re.compile(r"^\d+$")


def _parse_raw_register(raw: str | None) -> int | None:
    if raw in (None, "", "unavailable", "unknown"):
        return None
    text = str(raw).strip()
    if _INTEGER_RE.fullmatch(text):
        return int(text)
    return None


def _minor_from_pack_token_formatted(raw: str | None) -> int | None:
    """Extract sub-register minor from foxess_modbus formatted pack token (e.g. 0.004 → 4)."""
    if raw in (None, "", "unavailable", "unknown"):
        return None
    match = _PACK_TOKEN_RE.fullmatch(str(raw).strip())
    if not match:
        return None
    major = int(match.group(1))
    minor = int(match.group(2))
    if major == 0 and minor > 0:
        return minor
    return None


def format_evo_bcu_version(
    pack1_raw: str | None,
    pack2_raw: str | None = None,
    pack_count: str | None = None,
) -> str | None:
    """Decode Version_BCU from pack 1 token (37033) plus optional sub register (37034).

    On some EVO installs the minor revision lives in the next holding register when
    the pack token low bits are zero (37033=0x1000, 37034=4 → Fox 1.004).
    """
    count: int | None = None
    if pack_count not in (None, "", "unavailable", "unknown"):
        try:
            count = int(str(pack_count).strip())
        except ValueError:
            count = None
    pack1_int = _parse_raw_register(pack1_raw)
    pack2_int = _parse_raw_register(pack2_raw)
    if pack2_int is None:
        pack2_int = _minor_from_pack_token_formatted(pack2_raw)
    if (
        pack1_int is not None
        and (pack1_int & 0xFFF) == 0
        and pack2_int is not None
        and 0 < pack2_int < 0x1000
        and (count is None or count <= 1)
    ):
        merged = format_evo_pack_version(str(pack1_int | (pack2_int & 0xFFF)))
        if merged:
            return merged
    formatted = format_evo_pack_version(pack1_raw)
    if (
        formatted
        and formatted.endswith(".000")
        and pack2_int is not None
        and 0 < pack2_int < 0x1000
        and (count is None or count <= 1)
    ):
        major = formatted.split(".", 1)[0]
        return f"{major}.{pack2_int:03d}"
    return formatted


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
