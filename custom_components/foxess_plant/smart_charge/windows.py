"""Force charge / discharge window checks and Fox charge-period construction."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from ..models import ChargePeriodConfig


def periods_for_window(
    window: dict[str, Any],
    templates: list[ChargePeriodConfig],
) -> list[ChargePeriodConfig]:
    """Period 1 = force-charge the planned local HH:MM window; period 2 = template."""
    templates = list(templates or [])
    while len(templates) < 2:
        templates.append(ChargePeriodConfig())
    primary = ChargePeriodConfig.from_dict(templates[0].to_dict())
    primary.enable_force_charge = True
    primary.enable_charge_from_grid = True
    primary.start = str(window.get("start") or "00:00")
    primary.end = str(window.get("end") or "00:00")
    return [primary, ChargePeriodConfig.from_dict(templates[1].to_dict())]


def charge_periods_active_now(
    periods: list[ChargePeriodConfig],
    when: datetime | None = None,
    *,
    early_minutes: int = 1,
) -> bool:
    """True when local clock is inside (or just before) a force-charge HH:MM window.

    SmartCharge writes London-local start/end onto charge periods, but Modbus force
    charge is applied immediately when armed. Callers must only arm while this is True
    so a cheap overnight window is not force-charged during an afternoon period.
    """
    if not periods:
        return False
    local_now = dt_util.as_local(when or dt_util.now())
    early = timedelta(minutes=max(0, int(early_minutes)))
    for period in periods:
        if not getattr(period, "enable_force_charge", False):
            continue
        start_s = str(getattr(period, "start", "") or "").strip()
        end_s = str(getattr(period, "end", "") or "").strip()
        if not start_s or not end_s:
            continue
        try:
            start_h, start_m = (int(x) for x in start_s.split(":")[:2])
            end_h, end_m = (int(x) for x in end_s.split(":")[:2])
        except (TypeError, ValueError):
            continue
        start = local_now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        end = local_now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        if start_s == end_s:
            end = start + timedelta(minutes=30)
        elif end <= start:
            end += timedelta(days=1)
        if end <= local_now - early:
            start += timedelta(days=1)
            end += timedelta(days=1)
        if start - early <= local_now < end:
            return True
    return False


def discharge_window_active_now(
    window: dict[str, Any] | None,
    when: datetime | None = None,
    *,
    early_minutes: int = 1,
) -> bool:
    """True when local clock is inside (or just before) an export HH:MM window.

    Force Discharge is applied immediately when armed — only arm while this is True
    so a future peak slot is not discharged early.
    """
    if not window:
        return False
    start_s = str(window.get("start") or "").strip()
    end_s = str(window.get("end") or "").strip()
    if not start_s or not end_s:
        return False
    try:
        start_h, start_m = (int(x) for x in start_s.split(":")[:2])
        end_h, end_m = (int(x) for x in end_s.split(":")[:2])
    except (TypeError, ValueError):
        return False
    local_now = dt_util.as_local(when or dt_util.now())
    early = timedelta(minutes=max(0, int(early_minutes)))
    start = local_now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end = local_now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if start_s == end_s:
        end = start + timedelta(minutes=30)
    elif end <= start:
        end += timedelta(days=1)
    if end <= local_now - early:
        start += timedelta(days=1)
        end += timedelta(days=1)
    return start - early <= local_now < end
