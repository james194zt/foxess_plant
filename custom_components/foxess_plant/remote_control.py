"""EVO remote control fallback when charge-period Modbus writes are read-only."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .models import ChargePeriodConfig

_LOGGER = logging.getLogger(__name__)

REMOTE_CONTROL_IDLE = frozenset({"Disable", "unknown", "unavailable", None, ""})


def is_remote_control_active(state: str | None) -> bool:
    """True when the dedicated Remote Control select is commanding force charge/discharge."""
    return bool(state) and state not in REMOTE_CONTROL_IDLE


def is_charge_period_modbus_blocked(err: BaseException) -> bool:
    message = str(err)
    if "IllegalAddress" not in message:
        return False
    return any(
        token in message
        for token in ("48000", "48010", "48011", "48013", "48020", "48021", "48023", "Charge-period write failed")
    )


def periods_want_grid_force_charge(periods: list[ChargePeriodConfig]) -> bool:
    return any(p.enable_force_charge and p.enable_charge_from_grid for p in periods)


async def set_remote_control_mode(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    option: str,
) -> None:
    """Set foxess_modbus Remote Control select (Disable / Force Charge / Force Discharge)."""
    entity_id = entity_map.get("remote_control")
    if not entity_id:
        raise HomeAssistantError(
            "Remote Control entity not found. Update FoxESS Modbus to the latest version, "
            "restart Home Assistant, then reload FoxESS Plant."
        )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": option},
        blocking=True,
    )
    _LOGGER.info("Set %s to %s", entity_id, option)
