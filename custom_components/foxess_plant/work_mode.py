"""Work mode helpers — option aliases and live read matching for foxess_modbus."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .entity_live import async_read_entity_key_live

# Fox app / entity option spelling variants on different firmware builds.
WORK_MODE_ALIASES: dict[str, tuple[str, ...]] = {
    "Feed-in First": ("Feed-in Priority",),
    "Feed-in Priority": ("Feed-in First",),
    "Back-up": ("Back Up",),
    "Back Up": ("Back-up",),
}

# EVO 49203 values; writes use the same 1-based codes as reads (see foxess_modbus docs/evo).
EVO_WORK_MODE_READ_VALUES: dict[str, int] = {
    "Self Use": 1,
    "Feed-in First": 2,
    "Back-up": 3,
    "Peak Shaving": 4,
    "Remote Control": 255,
}


def resolve_work_mode_option(requested: str, options: list[str] | None) -> str:
    """Map a requested work mode to a valid foxess_modbus select option when possible."""
    if not options:
        return requested
    if requested in options:
        return requested
    for alt in WORK_MODE_ALIASES.get(requested, ()):
        if alt in options:
            return alt
    return requested


def work_mode_options_match(
    current: str | None,
    desired: str,
    options: list[str] | None,
) -> bool:
    """True when live entity state already matches the desired work mode option."""
    if not current or current in ("unknown", "unavailable"):
        return False
    resolved_desired = resolve_work_mode_option(desired, options)
    resolved_current = resolve_work_mode_option(current, options)
    return resolved_current == resolved_desired


async def async_read_work_mode_live(
    hass: HomeAssistant,
    entity_map: dict[str, str],
) -> str | None:
    return await async_read_entity_key_live(hass, entity_map, "work_mode")
