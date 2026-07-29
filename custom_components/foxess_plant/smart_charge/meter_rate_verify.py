"""Live smart-meter import rate double-check before SmartCharge force-charge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# When unit is missing, magnitudes above this are treated as already-pence.
_POUNDS_ABS_THRESHOLD = 2.5


@dataclass(frozen=True)
class MeterRateVerifyResult:
    status: str  # skipped | ok | mismatch | unavailable
    api_p_per_kwh: float | None
    meter_p_per_kwh: float | None
    delta_p: float | None
    tolerance_p: float
    entity_id: str | None
    detail: str
    blocks_arm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "api_p_per_kwh": self.api_p_per_kwh,
            "meter_p_per_kwh": self.meter_p_per_kwh,
            "delta_p": self.delta_p,
            "tolerance_p": self.tolerance_p,
            "entity_id": self.entity_id,
            "detail": self.detail,
            "blocks_arm": self.blocks_arm,
        }


def normalize_rate_to_pence(
    value: float,
    *,
    unit: str | None = None,
    api_hint_p: float | None = None,
) -> float:
    """Convert a live sensor reading to p/kWh.

    Prefer the entity ``unit_of_measurement``. When ambiguous (common for Glow),
    pick pounds×100 vs raw pence based on which is closer to the API rate — so
    ``-0.04`` pence is not mistaken for ``-4`` p after a blind ×100.
    """
    raw = float(value)
    unit_l = str(unit or "").strip().lower().replace(" ", "")
    if unit_l in ("p", "p/kwh", "pence", "pence/kwh"):
        return raw
    if "gbp" in unit_l or "£" in unit_l or unit_l in ("£/kwh", "gbp/kwh"):
        return raw * 100.0
    if unit_l.endswith("/kwh") and "p/" not in unit_l and "pence" not in unit_l:
        return raw * 100.0

    as_pence = raw
    as_pounds = raw * 100.0
    if api_hint_p is not None:
        if abs(as_pounds - float(api_hint_p)) < abs(as_pence - float(api_hint_p)):
            return as_pounds
        return as_pence
    if abs(raw) > _POUNDS_ABS_THRESHOLD:
        return as_pence
    return as_pounds


def rates_agree(api_p: float, meter_p: float, *, tolerance_p: float) -> bool:
    """True when API and meter are within tolerance (Glow often differs by ~0.01p)."""
    return abs(float(api_p) - float(meter_p)) <= max(0.0, float(tolerance_p))


def verify_meter_import_rate(
    *,
    enabled: bool,
    entity_id: str | None,
    api_p_per_kwh: float | None,
    meter_raw: float | None,
    meter_unit: str | None = None,
    tolerance_p: float = 0.5,
    recheck_minutes: int = 5,
) -> MeterRateVerifyResult:
    """Compare Octopus (API/cache) import rate with a live Glow/smart-meter sensor."""
    tol = max(0.0, float(tolerance_p))
    eid = str(entity_id or "").strip() or None
    if not enabled or not eid:
        return MeterRateVerifyResult(
            status="skipped",
            api_p_per_kwh=api_p_per_kwh,
            meter_p_per_kwh=None,
            delta_p=None,
            tolerance_p=tol,
            entity_id=eid,
            detail="Meter rate verify off or no sensor configured",
            blocks_arm=False,
        )
    if api_p_per_kwh is None:
        return MeterRateVerifyResult(
            status="skipped",
            api_p_per_kwh=None,
            meter_p_per_kwh=None,
            delta_p=None,
            tolerance_p=tol,
            entity_id=eid,
            detail="No API import rate to compare",
            blocks_arm=False,
        )
    if meter_raw is None:
        return MeterRateVerifyResult(
            status="unavailable",
            api_p_per_kwh=round(float(api_p_per_kwh), 4),
            meter_p_per_kwh=None,
            delta_p=None,
            tolerance_p=tol,
            entity_id=eid,
            detail=f"Meter sensor {eid} unavailable — proceeding without live check",
            blocks_arm=False,
        )

    api_p = float(api_p_per_kwh)
    meter_p = normalize_rate_to_pence(float(meter_raw), unit=meter_unit, api_hint_p=api_p)
    delta = meter_p - api_p
    if rates_agree(api_p, meter_p, tolerance_p=tol):
        return MeterRateVerifyResult(
            status="ok",
            api_p_per_kwh=round(api_p, 4),
            meter_p_per_kwh=round(meter_p, 4),
            delta_p=round(delta, 4),
            tolerance_p=tol,
            entity_id=eid,
            detail=(
                f"Meter {meter_p:.3f}p ≈ API {api_p:.3f}p "
                f"(Δ {delta:+.3f}p ≤ {tol:.2f}p)"
            ),
            blocks_arm=False,
        )

    mins = max(1, int(recheck_minutes))
    return MeterRateVerifyResult(
        status="mismatch",
        api_p_per_kwh=round(api_p, 4),
        meter_p_per_kwh=round(meter_p, 4),
        delta_p=round(delta, 4),
        tolerance_p=tol,
        entity_id=eid,
        detail=(
            f"Meter {meter_p:.3f}p vs API {api_p:.3f}p "
            f"(Δ {delta:+.3f}p > {tol:.2f}p) — recheck in {mins} min"
        ),
        blocks_arm=True,
    )
