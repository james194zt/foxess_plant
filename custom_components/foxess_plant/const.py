"""Constants for foxess_plant."""

DOMAIN = "foxess_plant"
PLATFORMS = ["sensor", "binary_sensor", "button"]

CONF_DEVICE_ID = "device_id"
CONF_INVERTER_TARGET = "inverter_target"
CONF_ENTITY_MAP = "entity_map"
CONF_BASELINE_PERIODS = "baseline_periods"
CONF_CONTROL = "control"
CONF_OVERRIDE = "override"
CONF_STORM_PREP = "storm_prep"
CONF_OUTAGE_PREP = "outage_prep"
CONF_FORECAST_PREP = "forecast_prep"
CONF_TARIFF_MODES = "tariff_modes"

CHARGE_PERIOD_KEYS = (
    "time_period_1_start",
    "time_period_1_end",
    "time_period_1_enable_force_charge",
    "time_period_1_enable_charge_from_grid",
    "time_period_2_start",
    "time_period_2_end",
    "time_period_2_enable_force_charge",
    "time_period_2_enable_charge_from_grid",
)

CONTROL_ENTITY_SUFFIXES = {
    "work_mode": "work_mode",
    "max_soc": "max_soc",
    "min_soc": "min_soc",
    "min_soc_on_grid": "min_soc_on_grid",
}

ANALYTICS_ENTITY_SUFFIXES = {
    "solar_energy_today": "solar_energy_today",
    "feed_in_energy_today": "feed_in_energy_today",
    "load_energy_today": "load_energy_today",
    "grid_consumption_energy_today": "grid_consumption_energy_today",
    "battery_discharge_today": "battery_discharge_today",
    "battery_charge_today": "battery_charge_today",
}

DISCOVERY_SUFFIXES = {
    **{k: k for k in CHARGE_PERIOD_KEYS},
    **CONTROL_ENTITY_SUFFIXES,
    **ANALYTICS_ENTITY_SUFFIXES,
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
MODE_OUTAGE = "outage"
MODE_TARIFF = "tariff"
MODE_FORECAST = "forecast"
MODE_MANUAL = "manual"

EVENT_PERIOD_APPLIED = f"{DOMAIN}_period_applied"
EVENT_PERIOD_APPLY_FAILED = f"{DOMAIN}_period_apply_failed"
EVENT_CONTROL_DRIFT = f"{DOMAIN}_control_drift"
EVENT_EXTERNAL_WRITE = f"{DOMAIN}_external_write_detected"
EVENT_STORM_ARMED = f"{DOMAIN}_storm_armed"
EVENT_STORM_DISARMED = f"{DOMAIN}_storm_disarmed"
EVENT_OUTAGE_ARMED = f"{DOMAIN}_outage_armed"
EVENT_OUTAGE_DISARMED = f"{DOMAIN}_outage_disarmed"
EVENT_FORECAST_ARMED = f"{DOMAIN}_forecast_armed"
EVENT_FORECAST_DISARMED = f"{DOMAIN}_forecast_disarmed"
EVENT_TARIFF_APPLIED = f"{DOMAIN}_tariff_applied"
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

DEFAULT_CONTROL = {
    "exclusive": True,
    "drift_check_interval": 300,
    "on_drift": "reapply",
}

DEFAULT_OVERRIDE = {
    "active": False,
    "mode": MODE_BASELINE,
    "periods": None,
    "reason": "",
    "saved_max_soc": None,
}

AUTOMATION_MODES = frozenset({MODE_STORM, MODE_OUTAGE, MODE_FORECAST})

DEFAULT_STORM_PREP = {
    "enabled": False,
    "trigger_entities": [],
    "charge_periods": [
        {
            "enable_force_charge": True,
            "enable_charge_from_grid": True,
            "start": "00:00",
            "end": "23:59",
        },
        {
            "enable_force_charge": False,
            "enable_charge_from_grid": False,
            "start": "00:00",
            "end": "00:00",
        },
    ],
    "target_max_soc": None,
}

DEFAULT_OUTAGE_PREP = {
    "enabled": False,
    "trigger_entities": [],
    "charge_periods": [
        {
            "enable_force_charge": True,
            "enable_charge_from_grid": True,
            "start": "00:00",
            "end": "23:59",
        },
        {
            "enable_force_charge": False,
            "enable_charge_from_grid": False,
            "start": "00:00",
            "end": "00:00",
        },
    ],
    "target_max_soc": None,
}

DEFAULT_FORECAST_PREP = {
    "enabled": False,
    "forecast_entity": None,
    "threshold_kwh": 5.0,
    "charge_periods": [
        {
            "enable_force_charge": True,
            "enable_charge_from_grid": True,
            "start": "00:30",
            "end": "05:00",
        },
        {
            "enable_force_charge": False,
            "enable_charge_from_grid": False,
            "start": "00:00",
            "end": "00:00",
        },
    ],
    "target_max_soc": None,
}

TRIGGER_ON_STATES = frozenset({"on", "true", "1", "active", "warning", "severe"})
