"""Parse and build Fox Cloud battery heating (warmup) API payloads."""

from __future__ import annotations

from typing import Any

DEFAULT_WARMUP_RANGES = {
    "start_min": 1,
    "start_max": 9,
    "end_min": 5,
    "end_max": 15,
}

DEFAULT_WARMUP_SLOTS = [
    {"enabled": False, "start": "00:00", "end": "00:00"},
    {"enabled": False, "start": "00:00", "end": "00:00"},
    {"enabled": False, "start": "00:00", "end": "00:00"},
]


def _enable_from_api(value: Any) -> bool:
    return str(value or "disable").strip().lower() == "enable"


def _resolve_data_list_item_value(item: dict[str, Any]) -> Any:
    """Resolve Fox dataList value; some devices return enum index instead of label."""
    value = item.get("value")
    enum_list = item.get("enumList")
    if not isinstance(enum_list, list) or not enum_list:
        return value
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for entry in enum_list:
        if str(entry).strip().lower() == text.lower():
            return str(entry)
    try:
        idx = int(text)
        if 0 <= idx < len(enum_list):
            return str(enum_list[idx])
    except (TypeError, ValueError):
        pass
    return text


def _flatten_battery_heating_data_list(
    result: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    data_list = (result or {}).get("dataList") if isinstance(result, dict) else None
    flat: dict[str, Any] = {}
    ci: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    if not isinstance(data_list, list):
        return flat, ci, rows
    for item in data_list:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        rows.append(item)
        value = _resolve_data_list_item_value(item)
        flat[name] = value
        ci[name.lower()] = value
    return flat, ci, rows


def _pick_flat_value(flat: dict[str, Any], ci: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in flat and flat[name] not in (None, ""):
            return flat[name]
        low = name.lower()
        if low in ci and ci[low] not in (None, ""):
            return ci[low]
    return None


def _warmup_state_from_rows(
    flat: dict[str, Any],
    ci: dict[str, Any],
    rows: list[dict[str, Any]],
) -> str | None:
    state = _pick_flat_value(
        flat,
        ci,
        "batteryWarmUpState",
        "BatteryWarmUpState",
        "batteryWarmUpStatus",
    )
    if state not in (None, ""):
        return str(state).strip() or None
    for item in rows:
        name = str(item.get("name") or "").lower()
        compact = name.replace("_", "")
        if "warmup" in compact and "state" in compact:
            resolved = _resolve_data_list_item_value(item)
            if resolved not in (None, ""):
                return str(resolved).strip() or None
    return None


def _warmup_enabled_from_flat(flat: dict[str, Any], ci: dict[str, Any]) -> bool:
    for key in ("batteryWarmUpEnable", "batteryWarmUpFunctionEnableFlag"):
        if _enable_from_api(_pick_flat_value(flat, ci, key)):
            return True
    return False


def _hm_from_parts(hour_key: str, minute_key: str, flat: dict[str, Any]) -> str:
    try:
        hour = int(flat.get(hour_key, 0) or 0)
    except (TypeError, ValueError):
        hour = 0
    try:
        minute = int(flat.get(minute_key, 0) or 0)
    except (TypeError, ValueError):
        minute = 0
    hour = max(0, min(23, hour))
    minute = max(0, min(59, minute))
    return f"{hour:02d}:{minute:02d}"


def _slot_from_flat(flat: dict[str, Any], prefix: str) -> dict[str, Any]:
    return {
        "enabled": _enable_from_api(flat.get(f"{prefix}Enable")),
        "start": _hm_from_parts(f"{prefix}StartHour", f"{prefix}StartMinute", flat),
        "end": _hm_from_parts(f"{prefix}EndHour", f"{prefix}EndMinute", flat),
    }


def parse_battery_heating_result(result: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize Fox Cloud batteryHeating/get result for the panel."""
    flat, ci, rows = _flatten_battery_heating_data_list(result)

    def _int(name: str, default: int) -> int:
        try:
            return int(_pick_flat_value(flat, ci, name) or default)
        except (TypeError, ValueError):
            return default

    ranges = {
        "start_min": _int("minStartTemperatureRange", DEFAULT_WARMUP_RANGES["start_min"]),
        "start_max": _int("maxStartTemperatureRange", DEFAULT_WARMUP_RANGES["start_max"]),
        "end_min": _int("minEndTemperatureRange", DEFAULT_WARMUP_RANGES["end_min"]),
        "end_max": _int("maxEndTemperatureRange", DEFAULT_WARMUP_RANGES["end_max"]),
    }

    return {
        "enabled": _warmup_enabled_from_flat(flat, ci),
        "start_temperature": _int("startTemperature", ranges["start_min"]),
        "end_temperature": _int("endTemperature", ranges["end_min"] + 5),
        "state": _warmup_state_from_rows(flat, ci, rows),
        "ranges": ranges,
        "slots": [
            _slot_from_flat(flat, "time1"),
            _slot_from_flat(flat, "time2"),
            _slot_from_flat(flat, "time3"),
        ],
    }


def default_battery_warmup_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "start_temperature": DEFAULT_WARMUP_RANGES["start_min"],
        "end_temperature": 10,
        "state": None,
        "ranges": dict(DEFAULT_WARMUP_RANGES),
        "slots": [dict(s) for s in DEFAULT_WARMUP_SLOTS],
    }


def _split_hm(value: str) -> tuple[int, int]:
    text = str(value or "00:00").strip()
    parts = text.split(":", 1)
    try:
        hour = int(parts[0])
    except (TypeError, ValueError, IndexError):
        hour = 0
    try:
        minute = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        minute = 0
    return max(0, min(23, hour)), max(0, min(59, minute))


def build_battery_heating_set_payload(config: dict[str, Any]) -> dict[str, str]:
    """Build body fields for batteryHeating/set (sn added by caller)."""
    slots = config.get("slots") or DEFAULT_WARMUP_SLOTS
    while len(slots) < 3:
        slots.append({"enabled": False, "start": "00:00", "end": "00:00"})

    payload: dict[str, str] = {
        "batteryWarmUpEnable": "enable" if config.get("enabled") else "disable",
        "startTemperature": str(int(config.get("start_temperature", 1))),
        "endTemperature": str(int(config.get("end_temperature", 10))),
    }

    for idx in range(3):
        slot = slots[idx] if isinstance(slots[idx], dict) else {}
        prefix = f"time{idx + 1}"
        sh, sm = _split_hm(slot.get("start", "00:00"))
        eh, em = _split_hm(slot.get("end", "00:00"))
        payload[f"{prefix}Enable"] = "enable" if slot.get("enabled") else "disable"
        payload[f"{prefix}StartHour"] = str(sh)
        payload[f"{prefix}StartMinute"] = str(sm)
        payload[f"{prefix}EndHour"] = str(eh)
        payload[f"{prefix}EndMinute"] = str(em)

    return payload


def validate_battery_warmup_config(config: dict[str, Any]) -> str | None:
    ranges = config.get("ranges") or DEFAULT_WARMUP_RANGES
    try:
        start = int(config.get("start_temperature"))
        end = int(config.get("end_temperature"))
    except (TypeError, ValueError):
        return "Start and end temperatures must be numbers"
    start_min = int(ranges.get("start_min", 1))
    start_max = int(ranges.get("start_max", 9))
    end_min = int(ranges.get("end_min", 5))
    end_max = int(ranges.get("end_max", 15))
    if start < start_min or start > start_max:
        return f"Start temperature must be between {start_min}°C and {start_max}°C"
    if end < end_min or end > end_max:
        return f"End temperature must be between {end_min}°C and {end_max}°C"
    if end <= start:
        return "End temperature must be above start temperature"
    return None
