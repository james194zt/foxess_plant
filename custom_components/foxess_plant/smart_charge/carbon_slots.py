"""Carbon intensity lookup for SmartCharge spread optimizer."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util


def carbon_for_instant(
    when: datetime,
    carbon_periods: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not carbon_periods:
        return None
    when_ms = int(dt_util.as_utc(when).timestamp() * 1000)
    for row in carbon_periods:
        start_ms = row.get("start_ms")
        end_ms = row.get("end_ms")
        if start_ms is None or end_ms is None:
            continue
        if int(start_ms) <= when_ms < int(end_ms):
            return row
    return None


def greener_night_active(
    when: datetime,
    greener_nights: list[dict[str, Any]],
) -> bool:
    """True when local time is 23:00–06:00 on a flagged greener night."""
    local = dt_util.as_local(when)
    hour = local.hour
    if not (hour >= 23 or hour < 6):
        return False
    night_date = local.date()
    if hour < 6:
        night_date = night_date - timedelta(days=1)
    date_key = night_date.isoformat()
    for row in greener_nights:
        if str(row.get("date")) == date_key and row.get("is_greener_night"):
            return True
    return False
