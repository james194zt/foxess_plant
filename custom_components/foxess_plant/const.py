"""Constants for foxess_plant."""

DOMAIN = "foxess_plant"
PLATFORMS = ["sensor", "binary_sensor", "button"]

CONF_DEVICE_ID = "device_id"
CONF_INVERTER_TARGET = "inverter_target"
CONF_ENTITY_MAP = "entity_map"
CONF_BASELINE_PERIODS = "baseline_periods"
CONF_CONTROL = "control"
CONF_OVERRIDE = "override"

DEFAULT_CONTROL = {
    "exclusive": True,
    "drift_check_interval": 300,
    "on_drift": "reapply",
}

# foxess_modbus entity key suffixes used for auto-discovery on the linked device
DISCOVERY_SUFFIXES = {
    "time_period_1_start": "time_period_1_start",
    "time_period_1_end": "time_period_1_end",
    "time_period_1_enable_force_charge": "time_period_1_enable_force_charge",
    "time_period_1_enable_charge_from_grid": "time_period_1_enable_charge_from_grid",
    "time_period_2_start": "time_period_2_start",
    "time_period_2_end": "time_period_2_end",
    "time_period_2_enable_force_charge": "time_period_2_enable_force_charge",
    "time_period_2_enable_charge_from_grid": "time_period_2_enable_charge_from_grid",
    "work_mode": "work_mode",
    "max_soc": "max_soc",
    "min_soc": "min_soc",
    "min_soc_on_grid": "min_soc_on_grid",
}

MODBUS_DOMAIN = "foxess_modbus"

ATTR_PLANT_ID = "plant_id"
ATTR_MODE = "mode"
ATTR_REASON = "reason"
ATTR_DESIRED = "desired"
ATTR_ACTUAL = "actual"

MODE_BASELINE = "baseline"
MODE_OVERRIDE = "override"
MODE_STORM = "storm"
MODE_TARIFF = "tariff"
MODE_MANUAL = "manual"

EVENT_PERIOD_APPLIED = f"{DOMAIN}_period_applied"
EVENT_PERIOD_APPLY_FAILED = f"{DOMAIN}_period_apply_failed"
EVENT_CONTROL_DRIFT = f"{DOMAIN}_control_drift"
EVENT_EXTERNAL_WRITE = f"{DOMAIN}_external_write_detected"
EVENT_STORM_ARMED = f"{DOMAIN}_storm_armed"
EVENT_STORM_DISARMED = f"{DOMAIN}_storm_disarmed"
EVENT_BASELINE_RESTORED = f"{DOMAIN}_baseline_restored"

DEFAULT_BASELINE_PERIODS = [
    {
        "enable_force_charge": False,
        "enable_charge_from_grid": False,
        "start": "00:00",
        "end": "00:00",
    },
    {
        "enable_force_charge": False,
        "enable_charge_from_grid": False,
        "start": "00:00",
        "end": "00:00",
    },
]

DEFAULT_OVERRIDE = {
    "active": False,
    "mode": MODE_BASELINE,
    "periods": None,
    "reason": "",
}
