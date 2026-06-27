"""Software-emulated system max SOC when hardware/cloud writes are unavailable."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .coordinator import FoxESSPlantCoordinator

CAP_SOURCE_STORM = "storm"
CAP_SOURCE_SMART_CHARGE = "smart_charge"
CAP_SOURCE_QUICK = "quick"
CAP_SOURCE_HARDWARE = "hardware"

FEED_IN_WORK_MODE_OPTIONS = ("Feed-in Priority", "Feed-in First")

# Fox app / entity option spelling variants on different firmware builds.
WORK_MODE_ALIASES: dict[str, tuple[str, ...]] = {
    "Feed-in First": ("Feed-in Priority",),
    "Feed-in Priority": ("Feed-in First",),
    "Back-up": ("Back Up",),
    "Back Up": ("Back-up",),
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


def smart_charge_max_cap(target_max_soc: float | None, max_target_soc: float) -> float:
    """Effective charging ceiling from SmartCharge config."""
    if target_max_soc is not None:
        return float(target_max_soc)
    return float(max_target_soc)


def resolve_virtual_max_soc_cap(coordinator: FoxESSPlantCoordinator) -> tuple[float | None, str | None]:
    """Return (cap_percent, source). StormSafe is the only override above SmartCharge."""
    plant = coordinator.plant

    if coordinator._active_storm_triggers:
        storm = plant.storm_prep
        cap = storm.target_max_soc
        return (float(cap) if cap is not None else 100.0), CAP_SOURCE_STORM

    sc = plant.smart_charge
    if sc.enabled and plant.control_active:
        return smart_charge_max_cap(sc.target_max_soc, sc.max_target_soc), CAP_SOURCE_SMART_CHARGE

    virtual = plant.virtual_soc.max_soc
    if virtual is not None:
        return float(virtual), CAP_SOURCE_QUICK

    entity_max = coordinator._entity_float("max_soc")
    if entity_max is not None and entity_max < 100:
        return float(entity_max), CAP_SOURCE_HARDWARE

    return None, None


def pick_feed_in_work_mode(options: list[str] | None) -> str | None:
    if not options:
        return None
    for name in FEED_IN_WORK_MODE_OPTIONS:
        if name in options:
            return name
    return None


def emulate_max_soc(coordinator: FoxESSPlantCoordinator) -> bool:
    """True when system max is enforced in software (hardware register 46610 unavailable)."""
    hw = coordinator.plant.virtual_soc.hardware_max_supported
    if hw is True:
        return False
    if hw is False:
        return True
    # Default: write register 46610; fall back to software cap only after a failed write.
    return False


def virtual_max_soc_message(max_soc: int) -> str:
    return (
        f"System max saved as a Fox Plant cap ({max_soc}%). "
        "Fox Plant stops charging at this level — the inverter register is not writable on this model."
    )


def virtual_soc_state(
    coordinator: FoxESSPlantCoordinator,
    *,
    cap_active: bool,
) -> dict[str, Any]:
    cap, source = resolve_virtual_max_soc_cap(coordinator)
    return {
        **coordinator.plant.virtual_soc.to_dict(),
        "emulate_max_soc": emulate_max_soc(coordinator),
        "effective_cap": cap,
        "cap_source": source,
        "cap_active": cap_active,
    }
