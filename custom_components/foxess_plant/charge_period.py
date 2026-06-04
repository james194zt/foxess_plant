"""Apply charge periods via foxess_modbus services."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import MODBUS_DOMAIN
from .discovery import missing_charge_period_entities
from .models import ChargePeriodConfig

_LOGGER = logging.getLogger(__name__)

_EVO_CHARGE_PERIOD_HINT = (
    "This error comes from the **FoxESS Modbus** integration (not Fox Plant). "
    "Charge-period entities are **read-only sensors** — changing them in Developer Tools → Set state "
    "does not write to the inverter. Use `foxess_modbus.update_all_charge_periods` instead. "
    "On EVO 10-H, writes use registers **48010–48012** (48000/48013 may not exist on your firmware). "
    "If IllegalAddress persists after disabling Mode Scheduler, your EVO firmware may not expose "
    "writable charge-period registers (mode @48013 unreadable is a common sign)."
)


def assert_charge_period_entities(entity_map: dict[str, str]) -> None:
    """Ensure foxess_modbus charge-period entities were discovered for this plant."""
    missing = missing_charge_period_entities(entity_map)
    if missing:
        raise HomeAssistantError(
            "Charge period entities are missing on the linked inverter "
            f"({', '.join(missing)}). Reload the FoxESS Plant integration after FoxESS Modbus "
            "has finished loading."
        )


def _raise_charge_period_error(err: BaseException) -> None:
    message = str(err)
    if "IllegalAddress" in message or "48010" in message or "48020" in message:
        raise HomeAssistantError(f"{_EVO_CHARGE_PERIOD_HINT} Details: {message}") from err
    if "does not support setting charge periods" in message:
        raise HomeAssistantError(
            "This inverter profile in FoxESS Modbus does not expose charge periods. "
            f"{message}"
        ) from err
    raise HomeAssistantError(message) from err


async def apply_charge_periods(
    hass: HomeAssistant,
    inverter_ref: str,
    periods: list[ChargePeriodConfig],
    *,
    entity_map: dict[str, str] | None = None,
) -> None:
    """Write charge periods through foxess_modbus (sole Modbus write path for plant policy).

    ``inverter_ref`` may be the foxess_modbus device ID or friendly name.
    """
    if not periods:
        raise HomeAssistantError("No charge periods provided")
    if entity_map is not None:
        assert_charge_period_entities(entity_map)

    payload: list[dict[str, Any]] = [p.to_service_dict() for p in periods]

    try:
        await hass.services.async_call(
            MODBUS_DOMAIN,
            "update_all_charge_periods",
            {"inverter": inverter_ref, "charge_periods": payload},
            blocking=True,
        )
    except Exception as err:
        _raise_charge_period_error(err)
    _LOGGER.debug("Applied %s charge period(s) to inverter %s", len(periods), inverter_ref)


async def apply_single_charge_period(
    hass: HomeAssistant,
    inverter_ref: str,
    period_index: int,
    period: ChargePeriodConfig,
) -> None:
    """Update one charge period via foxess_modbus."""
    try:
        await hass.services.async_call(
            MODBUS_DOMAIN,
            "update_charge_period",
            {
                "inverter": inverter_ref,
                "charge_period": period_index,
                **period.to_service_dict(),
            },
            blocking=True,
        )
    except Exception as err:
        _raise_charge_period_error(err)
