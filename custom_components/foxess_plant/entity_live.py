"""Poll foxess_modbus entities after homeassistant.update_entity (live inverter read)."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

ENTITY_REFRESH_SLEEP_S = 0.5
ENTITY_POLL_INTERVAL_S = 2.0
ENTITY_POLL_TIMEOUT_S = 30.0


async def async_refresh_entity_ids(hass: HomeAssistant, entity_ids: list[str]) -> None:
    tasks = []
    for entity_id in entity_ids:
        if entity_id:
            tasks.append(
                hass.services.async_call(
                    "homeassistant",
                    "update_entity",
                    {"entity_id": entity_id},
                    blocking=True,
                )
            )
    if tasks:
        await asyncio.gather(*tasks)
        await asyncio.sleep(ENTITY_REFRESH_SLEEP_S)


async def async_refresh_entity_keys(hass: HomeAssistant, entity_map: dict[str, str], keys: tuple[str, ...]) -> None:
    entity_ids = [entity_map[key] for key in keys if entity_map.get(key)]
    await async_refresh_entity_ids(hass, entity_ids)


def read_entity_state(hass: HomeAssistant, entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    return state.state if state else None


async def async_read_entity_key_live(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    key: str,
) -> str | None:
    entity_id = entity_map.get(key)
    if not entity_id:
        return None
    await async_refresh_entity_ids(hass, [entity_id])
    return read_entity_state(hass, entity_id)


async def async_poll_entity_id_live(
    hass: HomeAssistant,
    entity_id: str,
    *,
    expected: str | Callable[[str | None], bool],
    timeout_s: float = ENTITY_POLL_TIMEOUT_S,
    poll_interval_s: float = ENTITY_POLL_INTERVAL_S,
) -> tuple[bool, str | None, float, int]:
    """Poll a single entity until it matches expected after live refresh."""
    loop = asyncio.get_running_loop()
    start = loop.time()
    attempts = 0
    final: str | None = None
    while True:
        attempts += 1
        await async_refresh_entity_ids(hass, [entity_id])
        final = read_entity_state(hass, entity_id)
        matched = expected(final) if callable(expected) else final == expected
        if matched:
            return True, final, loop.time() - start, attempts
        if loop.time() - start >= timeout_s:
            return False, final, loop.time() - start, attempts
        await asyncio.sleep(poll_interval_s)


async def async_poll_entity_key_live(
    hass: HomeAssistant,
    entity_map: dict[str, str],
    key: str,
    *,
    expected: str | Callable[[str | None], bool],
    timeout_s: float = ENTITY_POLL_TIMEOUT_S,
    poll_interval_s: float = ENTITY_POLL_INTERVAL_S,
) -> tuple[bool, str | None, float, int]:
    """Poll until key matches expected after refreshing from the inverter."""
    entity_id = entity_map.get(key)
    if not entity_id:
        return False, None, 0.0, 0
    return await async_poll_entity_id_live(
        hass,
        entity_id,
        expected=expected,
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
    )


async def async_read_soc_live(hass: HomeAssistant, entity_map: dict[str, str]) -> dict[str, int]:
    from .soc_limits import read_soc_current

    from .soc_limits import SOC_KEYS

    await async_refresh_entity_keys(hass, entity_map, SOC_KEYS)
    return read_soc_current(hass, entity_map)
