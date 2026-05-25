"""Apply charge periods via foxess_modbus services."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import MODBUS_DOMAIN
from .models import ChargePeriodConfig

_LOGGER = logging.getLogger(__name__)


async def apply_charge_periods(
    hass: HomeAssistant,
    inverter_target: str,
    periods: list[ChargePeriodConfig],
) -> None:
    """Write charge periods through foxess_modbus (sole Modbus write path for plant policy)."""
    if not periods:
        raise HomeAssistantError("No charge periods provided")

    payload: list[dict[str, Any]] = [p.to_service_dict() for p in periods]

    await hass.services.async_call(
        MODBUS_DOMAIN,
        "update_all_charge_periods",
        {"inverter": inverter_target, "charge_periods": payload},
        blocking=True,
    )
    _LOGGER.debug("Applied %s charge period(s) to inverter %s", len(periods), inverter_target)


async def apply_single_charge_period(
    hass: HomeAssistant,
    inverter_target: str,
    period_index: int,
    period: ChargePeriodConfig,
) -> None:
    """Update one charge period via foxess_modbus."""
    await hass.services.async_call(
        MODBUS_DOMAIN,
        "update_charge_period",
        {
            "inverter": inverter_target,
            "charge_period": period_index,
            **period.to_service_dict(),
        },
        blocking=True,
    )
