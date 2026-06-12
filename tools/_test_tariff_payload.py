#!/usr/bin/env python3
"""Quick sanity check for tariff save payload parsing."""
from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components"))

ha_util = types.ModuleType("homeassistant.util.dt")
ha_util.now = lambda: datetime.now(timezone.utc)
ha_util.as_local = lambda dt: dt
ha_util.as_utc = lambda dt: dt
ha_util.UTC = timezone.utc
ha_util.parse_datetime = lambda s: datetime.fromisoformat(s)
sys.modules["homeassistant"] = types.ModuleType("homeassistant")
sys.modules["homeassistant.util"] = types.ModuleType("homeassistant.util")
sys.modules["homeassistant.util.dt"] = ha_util
sys.modules["homeassistant.core"] = types.ModuleType("homeassistant.core")
sys.modules["homeassistant.helpers"] = types.ModuleType("homeassistant.helpers")
sys.modules["homeassistant.helpers.entity_registry"] = types.ModuleType(
    "homeassistant.helpers.entity_registry"
)

from foxess_plant.models import TariffConfig

payload = {
    "kind": "static",
    "currency": "GBP",
    "import_source": "entity",
    "import_entity": "sensor.octopus_import",
    "import_p_per_kwh": 0,
    "export_source": "schedule",
    "export_entity": None,
    "export_p_per_kwh": 28.16,
    "standing_source": "entity",
    "standing_entity": "sensor.glow_standing",
    "standing_charge_p_per_day": 0,
    "schedule": {
        "hours": [1] * 7 + [0] * 17,
        "bands": [
            {"import_p_per_kwh": 0, "export_p_per_kwh": 28.16},
            {"import_p_per_kwh": 0, "export_p_per_kwh": 9.0},
            {"import_p_per_kwh": 0, "export_p_per_kwh": 0},
            {"import_p_per_kwh": 0, "export_p_per_kwh": 0},
        ],
    },
}
cfg = TariffConfig.from_dict(payload)
print("configured:", cfg.configured())
print("export band0:", cfg.schedule_config().bands[0].export_p_per_kwh)
