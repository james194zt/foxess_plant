"""Constants for foxess_plant."""

from datetime import timedelta

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
CONF_PANEL_DISPLAY = "panel_display"
CONF_PV_CONFIG = "pv_config"
CONF_SOLCAST = "solcast"
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

IMPACT_ENTITY_SUFFIXES = {
    "solar_energy_total": "solar_energy_total",
    "feed_in_energy_total": "feed_in_energy_total",
    **{f"pv{i}_energy_total": f"pv{i}_energy_total" for i in range(1, 7)},
}

DISCOVERY_SUFFIXES = {
    **{k: k for k in CHARGE_PERIOD_KEYS},
    **CONTROL_ENTITY_SUFFIXES,
    **ANALYTICS_ENTITY_SUFFIXES,
    **IMPACT_ENTITY_SUFFIXES,
}

# Panel live-data keys → candidate entity_id / unique_id suffixes (first match wins).
# PCS / BMS identity and firmware (first matching entity suffix wins).
IDENTITY_ENTITY_SUFFIXES: dict[str, tuple[str, ...]] = {
    "pcs_model_name": ("pcs_model_name", "inverter_model_name"),
    "pcs_serial_number": ("pcs_serial_number", "inverter_serial_number"),
    "modbus_protocol_version": ("modbus_protocol_version",),
    "master_version": ("master_version",),
    "slave_version": ("slave_version",),
    "manager_version": ("manager_version",),
    "bms_online": ("bms_online",),
    "bms_pack_serial_modbus": ("bms_pack_serial_modbus",),
    "bms_pack_count": ("bms_pack_count",),
    "bms_pack_1_version": ("bms_pack_1_version",),
    "bms_pack_2_version": ("bms_pack_2_version",),
    "bms_pack_3_version": ("bms_pack_3_version",),
    "bms_pack_4_version": ("bms_pack_4_version",),
    "grid_status": ("grid_status",),
    "inverter_state": ("inverter_state",),
}

PANEL_ENTITY_SUFFIXES: dict[str, tuple[str, ...]] = {
    "pv_power": ("pv1_power", "pv_power", "pv_power_total", "pv_power_evo_10"),
    "load_power": ("load_power", "load_power_total"),
    "grid_import": ("grid_consumption",),
    "grid_export": ("feed_in", "grid_ct"),
    "battery_soc": ("battery_soc_1", "battery_soc"),
    "battery_power": ("invbatpower_1", "invbatpower", "battery_power"),
    "battery_charge": ("battery_charge_1", "battery_charge"),
    "battery_discharge": ("battery_discharge_1", "battery_discharge"),
    "battery_status": ("battery_status",),
    "bms_temp_low": ("bms_cell_temp_low_1", "bms_cell_temp_low"),
}

PANEL_URL_PATH = "foxess-plant"
PANEL_TITLE = "Fox Plant"
# Sidebar still uses MDI; Fox logo is shown in-panel via brand/ + brands API (same as modbus).
PANEL_ICON = "mdi:solar-power-variant"
PANEL_STATIC_URL = "/foxess_plant_panel"
PANEL_BRAND_ICON_STATIC = f"{PANEL_STATIC_URL}/icon.png"

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

GOOGLE_WEATHER_DOMAIN = "google_weather"
STORM_ALERT_PROVIDER_GOOGLE = "google_weather"
STORM_ALERT_PROVIDER_SOLCAST = "solcast"

SOLCAST_AUTO_UPDATE_DAYLIGHT = "daylight"
SOLCAST_AUTO_UPDATE_ALL_DAY = "all_day"

DEFAULT_SOLCAST_API_LIMIT = 10
# Match precision shown on Solcast hobbyist site locations (avoid HA extra decimals).
SOLCAST_COORDINATE_DECIMALS = 4
SOLCAST_ACCOUNT_LOCATIONS_URL = "https://toolkit.solcast.com.au/account/locations"
# Stop Solcast PV polls this long before sunset (no useful yield after).
SOLCAST_POLL_END_BEFORE_SUNSET = timedelta(hours=1)
SOLCAST_MIN_POLL_INTERVAL = timedelta(minutes=15)
DEFAULT_STORM_SOLCAST_CAPE_THRESHOLD = 800.0
DEFAULT_STORM_SOLCAST_PRECIP_MM_H = 2.0
DEFAULT_STORM_SOLCAST_WEATHER_KEYWORDS: frozenset[str] = frozenset(
    {
        "thunder",
        "storm",
        "hail",
        "tornado",
        "hurricane",
        "blizzard",
        "heavy rain",
        "heavy shower",
        "severe",
    }
)
GOOGLE_WEATHER_ALERT_SUFFIXES = (
    "_weather_alert",
    "_severe_weather_alert",
    "_urgent_weather_alert",
)

DEFAULT_STORM_FORECAST_LEAD_HOURS = 4

DEFAULT_STORM_PREP = {
    "enabled": False,
    "alert_provider": STORM_ALERT_PROVIDER_GOOGLE,
    "google_weather_entry_id": None,
    "use_weather_condition": True,
    "use_forecast_lead": True,
    "forecast_lead_hours": DEFAULT_STORM_FORECAST_LEAD_HOURS,
    "condition_entity_id": None,
    "weather_entity_id": None,
    "storm_google_types": None,
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

DEFAULT_PANEL_DISPLAY = {
    "forecast_entity_id": None,
}

DEFAULT_PV_STRING = {
    "enabled": True,
    "panel_count": 6,
    "watts_per_panel": 450,
    "efficiency_factor": 100.0,
    "tilt": 25,
    "azimuth": 180,
}

DEFAULT_SOLCAST = {
    "enabled": False,
    "api_key": None,
    "api_limit": DEFAULT_SOLCAST_API_LIMIT,
    "auto_update": SOLCAST_AUTO_UPDATE_DAYLIGHT,
    "fetch_pv_forecast": True,
    "latitude": None,
    "longitude": None,
    "period": "PT30M",
    "api_used_today": 0,
    "api_used_date": None,
    "last_fetch_at": None,
    "last_error": None,
}

DEFAULT_PV_CONFIG = {
    "pv1": DEFAULT_PV_STRING,
    "pv2": {
        "enabled": False,
        "panel_count": 1,
        "watts_per_panel": 450,
        "efficiency_factor": 100.0,
        "tilt": 25,
        "azimuth": 180,
    },
}

TRIGGER_ON_STATES = frozenset({"on", "true", "1", "active", "warning", "severe"})
