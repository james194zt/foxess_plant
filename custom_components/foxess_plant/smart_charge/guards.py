"""Pure guards for SmartCharge evaluation (storm/outage priority)."""

from __future__ import annotations

from typing import Any


def smart_charge_evaluation_blocked(
    *,
    enabled: bool,
    control_active: bool,
    outage_prep_enabled: bool,
    active_outage_triggers: list[Any] | None,
    storm_prep_enabled: bool,
    active_storm_triggers: list[Any] | None,
) -> str | None:
    """Return block reason when SmartCharge must not run; None if evaluation may proceed."""
    if not enabled or not control_active:
        return "inactive"
    if outage_prep_enabled and active_outage_triggers:
        return "outage"
    if storm_prep_enabled and active_storm_triggers:
        return "storm"
    return None
