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


def _group_enabled(group: dict[str, Any]) -> bool:
    enable = group.get("enable")
    if enable is None:
        return True
    parsed = _as_bool(enable)
    return parsed if parsed is not None else True


def scheduler_schedule_active(schedule: dict[str, Any] | None) -> bool:
    """True when V3/V2 schedule has master on or any segment enabled."""
    raw = schedule if isinstance(schedule, dict) else {}
    master = _as_bool(raw.get("enable"))
    if master is True:
        return True
    groups = raw.get("groups")
    if not isinstance(groups, list):
        return False
    return any(_group_enabled(g) for g in groups if isinstance(g, dict))


def scheduler_active_groups_count(schedule: dict[str, Any] | None) -> int:
    groups = (schedule or {}).get("groups") if isinstance(schedule, dict) else None
    if not isinstance(groups, list):
        return 0
    return sum(1 for g in groups if isinstance(g, dict) and _group_enabled(g))


def scheduler_has_cloud_max_soc(schedule: dict[str, Any] | None) -> bool:
    groups = (schedule or {}).get("groups") if isinstance(schedule, dict) else None
    if not isinstance(groups, list):
        return False
    for group in groups:
        if not isinstance(group, dict) or not _group_enabled(group):
            continue
        extra = group.get("extraParam")
        if isinstance(extra, dict) and extra.get("maxSoc") is not None:
            return True
        if group.get("maxSoc") is not None:
            return True
    return False


def merge_scheduler_state(
    flag: dict[str, Any] | None,
    schedule: dict[str, Any] | None,
) -> dict[str, Any]:
    """Combine get/flag and V3/V2 schedule into one panel/coordinator view."""
    normalized = normalize_scheduler_flag(flag)
    segments_active = scheduler_schedule_active(schedule)
    active_groups = scheduler_active_groups_count(schedule)
    cloud_max_soc = scheduler_has_cloud_max_soc(schedule)
    flag_enabled = scheduler_flag_enabled(normalized)
    enabled = flag_enabled or segments_active
    return {
        **normalized,
        "flag_enabled": flag_enabled,
        "enabled": enabled,
        "segments_active": segments_active,
        "active_groups": active_groups,
        "cloud_max_soc": cloud_max_soc,
        "scheduler_version": "v3" if schedule else None,
    }


def build_disable_schedule_body(device_sn: str, schedule: dict[str, Any] | None) -> dict[str, Any]:
    """Build Fox scheduler/enable body that clears active segments (all enable=0)."""
    groups_in = schedule.get("groups") if isinstance(schedule, dict) else None
    groups_out: list[dict[str, Any]] = []
    if isinstance(groups_in, list):
        for group in groups_in:
            if not isinstance(group, dict):
                continue
            item: dict[str, Any] = {
                "enable": 0,
                "startHour": int(group.get("startHour", 0) or 0),
                "startMinute": int(group.get("startMinute", 0) or 0),
                "endHour": int(group.get("endHour", 0) or 0),
                "endMinute": int(group.get("endMinute", 59) or 59),
                "workMode": str(group.get("workMode") or "SelfUse"),
            }
            extra = group.get("extraParam")
            if isinstance(extra, dict):
                cleaned = {k: v for k, v in extra.items() if k != "maxSoc"}
                if cleaned:
                    item["extraParam"] = cleaned
            for key in ("minSocOnGrid", "fdSoc", "fdPwr", "maxSoc"):
                if key in group and key not in item.get("extraParam", {}):
                    item.setdefault("extraParam", {})[key] = group[key]
            if isinstance(item.get("extraParam"), dict):
                item["extraParam"].pop("maxSoc", None)
                if not item["extraParam"]:
                    item.pop("extraParam")
            groups_out.append(item)
    if not groups_out:
        groups_out = [
            {
                "enable": 0,
                "startHour": 0,
                "startMinute": 0,
                "endHour": 0,
                "endMinute": 1,
                "workMode": "SelfUse",
                "minSocOnGrid": 10,
                "fdSoc": 10,
                "fdPwr": 0,
            }
        ]
    return {"deviceSN": str(device_sn).strip(), "groups": groups_out}


def build_max_soc_schedule_body(
    device_sn: str,
    max_soc: int,
    schedule: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build scheduler/enable body with maxSoc set on each segment (EVO cloud path)."""
    max_v = max(10, min(100, int(max_soc)))
    groups_in = schedule.get("groups") if isinstance(schedule, dict) else None
    groups_out: list[dict[str, Any]] = []
    if isinstance(groups_in, list):
        for group in groups_in:
            if not isinstance(group, dict):
                continue
            extra = dict(group.get("extraParam") or {})
            for key in ("minSocOnGrid", "fdSoc", "fdPwr"):
                if key in group and key not in extra:
                    extra[key] = group[key]
            extra["maxSoc"] = max_v
            item: dict[str, Any] = {
                "enable": int(group.get("enable", 1) or 0),
                "startHour": int(group.get("startHour", 0) or 0),
                "startMinute": int(group.get("startMinute", 0) or 0),
                "endHour": int(group.get("endHour", 23) or 23),
                "endMinute": int(group.get("endMinute", 59) or 59),
                "workMode": str(group.get("workMode") or "SelfUse"),
                "minSocOnGrid": int(extra.get("minSocOnGrid", 10) or 10),
                "fdSoc": int(extra.get("fdSoc", max(max_v, 10)) or max(max_v, 10)),
                "fdPwr": int(extra.get("fdPwr", 6000) or 6000),
                "maxSoc": max_v,
                "extraParam": extra,
            }
            groups_out.append(item)
    if not groups_out:
        groups_out = [
            {
                "enable": 1,
                "startHour": 0,
                "startMinute": 0,
                "endHour": 23,
                "endMinute": 59,
                "workMode": "SelfUse",
                "minSocOnGrid": 10,
                "fdSoc": max(max_v, 10),
                "fdPwr": 6000,
                "maxSoc": max_v,
                "extraParam": {
                    "minSocOnGrid": 10,
                    "fdSoc": max(max_v, 10),
                    "fdPwr": 6000,
                    "maxSoc": max_v,
                },
            }
        ]
    return {"deviceSN": str(device_sn).strip(), "groups": groups_out}


def scheduler_status_label(flag: dict[str, Any] | None) -> str:
    if not flag:
        return "Unknown"
    supported = flag.get("supported")
    if supported is False:
        return "Not supported"
    segments = int(flag.get("active_groups") or 0)
    cloud_max = bool(flag.get("cloud_max_soc"))
    if scheduler_flag_enabled(flag):
        if segments:
            return f"Enabled — {segments} active segment(s) block Modbus max SOC"
        return "Enabled — blocks some Modbus SOC writes"
    if segments:
        extra = " (cloud max SOC in schedule)" if cloud_max else ""
        return f"Flag off — {segments} segment(s) still active{extra}"
    if supported is True:
        return "Disabled"
    return "Disabled"
