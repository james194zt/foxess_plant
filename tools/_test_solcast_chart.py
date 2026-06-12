#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.foxess_plant.solcast_forecast_chart import (
    build_forecast_intraday_chart,
    build_statistics_forecast_overlay,
)

stored = {"history": [], "current": None}
cache = {}
print("empty", build_forecast_intraday_chart(None, stored, cache))

cache2 = {
    "pv_forecast_parsed": {
        "detailed_forecast": [
            {"period_start": "2026-05-28T06:00:00+01:00", "pv_estimate": 1.0},
            {"period_start": "2026-05-28T12:00:00+01:00", "pv_estimate": 2.0},
            {"period_start": "2026-05-28T18:00:00+01:00", "pv_estimate": 0.5},
        ],
        "period_count": 3,
    },
    "updated_at": "2026-05-28T08:00:00+01:00",
}
pts = build_forecast_intraday_chart(None, stored, cache2)
print("points", len(pts))
ov = build_statistics_forecast_overlay(None, stored, cache2)
print("overlay", len(ov))
