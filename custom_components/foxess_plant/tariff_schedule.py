"""Time-of-use tariff schedule — hourly bands and rate resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

TARIFF_BAND_COUNT = 4
TARIFF_HOUR_COUNT = 24

TARIFF_SOURCE_SCHEDULE = "schedule"
TARIFF_SOURCE_PLUGIN = "plugin"


@dataclass
class TariffBandConfig:
    """One of up to four daily rate bands (import + export per band)."""

    import_p_per_kwh: float = 0.0
    export_p_per_kwh: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> TariffBandConfig:
        raw = data if isinstance(data, dict) else {}

        def _rate(key: str) -> float:
            try:
                return max(0.0, float(raw.get(key, 0) or 0))
            except (TypeError, ValueError):
                return 0.0

        return cls(import_p_per_kwh=_rate("import_p_per_kwh"), export_p_per_kwh=_rate("export_p_per_kwh"))

    def to_dict(self) -> dict[str, float]:
        return {
            "import_p_per_kwh": round(self.import_p_per_kwh, 4),
            "export_p_per_kwh": round(self.export_p_per_kwh, 4),
        }


@dataclass
class TariffScheduleConfig:
    """Fixed weekly schedule: 24 hourly slots mapped to rate bands."""

    hours: list[int] = field(default_factory=lambda: [0] * TARIFF_HOUR_COUNT)
    bands: list[TariffBandConfig] = field(
        default_factory=lambda: [TariffBandConfig() for _ in range(TARIFF_BAND_COUNT)]
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> TariffScheduleConfig:
        raw = data if isinstance(data, dict) else {}
        hours_raw = raw.get("hours")
        hours: list[int] = []
        if isinstance(hours_raw, list):
            for value in hours_raw[:TARIFF_HOUR_COUNT]:
                try:
                    band = int(value)
                except (TypeError, ValueError):
                    band = 0
                hours.append(max(0, min(TARIFF_BAND_COUNT - 1, band)))
        while len(hours) < TARIFF_HOUR_COUNT:
            hours.append(0)

        bands_raw = raw.get("bands")
        bands: list[TariffBandConfig] = []
        if isinstance(bands_raw, list):
            for item in bands_raw[:TARIFF_BAND_COUNT]:
                bands.append(TariffBandConfig.from_dict(item if isinstance(item, dict) else {}))
        while len(bands) < TARIFF_BAND_COUNT:
            bands.append(TariffBandConfig())
        return cls(hours=hours, bands=bands)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hours": list(self.hours),
            "bands": [band.to_dict() for band in self.bands],
        }

    def band_index_for_hour(self, hour: int) -> int:
        if 0 <= hour < len(self.hours):
            return max(0, min(TARIFF_BAND_COUNT - 1, int(self.hours[hour])))
        return 0

    def band_for_hour(self, hour: int) -> TariffBandConfig:
        return self.bands[self.band_index_for_hour(hour)]

    def rates_at(self, when: datetime | None = None) -> dict[str, Any]:
        """Resolve import/export minor-unit rates for a local datetime."""
        local = dt_util.as_local(when or dt_util.now())
        hour = local.hour
        band_idx = self.band_index_for_hour(hour)
        band = self.bands[band_idx]
        return {
            "hour": hour,
            "band_index": band_idx,
            "import_p_per_kwh": band.import_p_per_kwh,
            "export_p_per_kwh": band.export_p_per_kwh,
        }


def default_schedule() -> TariffScheduleConfig:
    return TariffScheduleConfig()


def migrate_legacy_manual_to_schedule(
    schedule: TariffScheduleConfig,
    *,
    import_p: float = 0.0,
    export_p: float = 0.0,
) -> TariffScheduleConfig:
    """Seed band 0 from legacy flat manual rates when schedule bands are empty."""
    bands = list(schedule.bands)
    if import_p > 0 and bands[0].import_p_per_kwh <= 0:
        bands[0] = TariffBandConfig(
            import_p_per_kwh=import_p,
            export_p_per_kwh=bands[0].export_p_per_kwh,
        )
    if export_p > 0 and bands[0].export_p_per_kwh <= 0:
        bands[0] = TariffBandConfig(
            import_p_per_kwh=bands[0].import_p_per_kwh,
            export_p_per_kwh=export_p,
        )
    return TariffScheduleConfig(hours=list(schedule.hours), bands=bands)


def next_schedule_boundary(when: datetime | None = None) -> datetime:
    """Next local midnight hour boundary (top of the hour)."""
    local = dt_util.as_local(when or dt_util.now())
    nxt = local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return dt_util.as_utc(nxt)


def tariff_sensor_unique_id(entry_id: str, kind: str) -> str:
    return f"{entry_id}_tariff_{kind}_rate"


def tariff_plugin_entity_id(hass, entry_id: str, kind: str) -> str | None:
    from homeassistant.helpers import entity_registry as er

    reg = er.async_get(hass)
    if reg is None:
        return None
    return reg.async_get_entity_id("sensor", "foxess_plant", tariff_sensor_unique_id(entry_id, kind))
