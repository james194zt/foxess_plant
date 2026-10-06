"""Only leftovers are removed: entities of a deleted install, or listed retired unique ids of this one."""

from types import SimpleNamespace

from custom_components.foxess_plant.stale_entities import stale_entity_ids

CURRENT = "01KSHB86DCW29SB00TC1DCWXHJ"
GONE = "01KSGJD7ZKH7GMYF3433J7HXXJ"


def _e(entity_id: str, entry_id: str, suffix: str, platform: str = "foxess_plant") -> SimpleNamespace:
    return SimpleNamespace(entity_id=entity_id, config_entry_id=entry_id, unique_id=f"{entry_id}_{suffix}", platform=platform)


def test_leftovers_found_and_live_entities_kept() -> None:
    entries = [
        _e("binary_sensor.old_control_active", GONE, "control_active"),  # install that no longer exists
        _e("sensor.solcast_pv_power_now", CURRENT, "solcast_pv_power_now"),  # retired name
        _e("sensor.solcast_pv_forecast_remaining_today", CURRENT, "solcast_pv_forecast_remaining"),
        _e("sensor.power_now", CURRENT, "solcast_power_now"),  # its replacement: kept
        _e("sensor.performance_pv_power", CURRENT, "performance_pv_power"),  # kept
        _e("sensor.evo_10_pv1_power", "modbus-entry", "pv1_power", platform="foxess_modbus"),  # other integration
    ]
    assert stale_entity_ids(entries, CURRENT, {CURRENT}) == [
        "binary_sensor.old_control_active",
        "sensor.solcast_pv_forecast_remaining_today",
        "sensor.solcast_pv_power_now",
    ]


def test_a_second_live_install_is_left_alone() -> None:
    other = "01OTHERPLANT"
    entries = [_e("sensor.other_plant_mode", other, "plant_mode")]
    assert stale_entity_ids(entries, CURRENT, {CURRENT, other}) == []
