"""Export mode thresholds — no Home Assistant dependency."""

from __future__ import annotations

from typing import Any

OPERATING_MODE_MAX_PROFIT = "max_profit"
OPERATING_MODE_MAX_SAFETY = "max_safety"
OPERATING_MODE_MAX_GREEN = "max_green"


def _config_float(config: Any, key: str, default: float) -> float:
    try:
        return float(getattr(config, key, default) or default)
    except (TypeError, ValueError):
        return default


def mode_export_limits(operating_mode: str, config: Any) -> tuple[float, float]:
    """Return (min_export_p_per_kwh, exportable_fraction)."""
    if operating_mode == OPERATING_MODE_MAX_PROFIT:
        return (
            _config_float(config, "min_export_p_profit", 12.0),
            _config_float(config, "exportable_fraction_profit", 1.0),
        )
    if operating_mode == OPERATING_MODE_MAX_GREEN:
        return (
            _config_float(config, "min_export_p_green", 25.0),
            _config_float(config, "exportable_fraction_green", 0.15),
        )
    return (
        _config_float(config, "min_export_p_safety", 20.0),
        _config_float(config, "exportable_fraction_safety", 0.35),
    )


def export_allowed_for_mode(operating_mode: str, config: Any) -> bool:
    if not bool(getattr(config, "export_enabled", True)):
        return False
    if operating_mode == OPERATING_MODE_MAX_GREEN:
        return bool(getattr(config, "export_enabled_green", False))
    if operating_mode == OPERATING_MODE_MAX_SAFETY:
        return bool(getattr(config, "export_enabled_safety", True))
    return True
