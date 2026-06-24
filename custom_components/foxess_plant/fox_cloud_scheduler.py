"""Fox Cloud mode scheduler (get/set flag) helpers."""

from __future__ import annotations

from typing import Any


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) != 0
    text = str(value).strip().lower()
    if text in ("1", "true", "on", "enable", "enabled", "yes"):
        return True
    if text in ("0", "false", "off", "disable", "disabled", "no"):
        return False
    return None


def normalize_scheduler_flag(result: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize scheduler get/flag API result for the panel."""
    raw = result if isinstance(result, dict) else {}
    supported = _as_bool(raw.get("support"))
    if supported is None:
        supported = _as_bool(raw.get("supported"))
    enabled = _as_bool(raw.get("enable"))
    if enabled is None:
        enabled = _as_bool(raw.get("enabled"))
    return {
        "supported": supported,
        "enabled": enabled,
    }


def scheduler_flag_enabled(flag: dict[str, Any] | None) -> bool:
    return bool((flag or {}).get("enabled"))


def scheduler_status_label(flag: dict[str, Any] | None) -> str:
    if not flag:
        return "Unknown"
    supported = flag.get("supported")
    if supported is False:
        return "Not supported"
    if scheduler_flag_enabled(flag):
        return "Enabled — blocks some Modbus SOC writes"
    if supported is True:
        return "Disabled"
    return "Disabled"
