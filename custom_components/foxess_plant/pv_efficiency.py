"""PV efficiency factor from Solcast installation age (monthly anniversary derating)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

from .solcast_weather import parse_solcast_installation_date

if TYPE_CHECKING:
    from .models import PvSystemConfig


def _coerce_install_date(install_date: str | date | None) -> date | None:
    if install_date is None:
        return None
    if isinstance(install_date, date):
        return install_date
    parsed = parse_solcast_installation_date(install_date)
    if not parsed:
        return None
    parts = [int(x) for x in parsed.split("-")]
    return date(parts[0], parts[1], parts[2])


def months_since_installation(
    install_date: str | date | None,
    ref: date | None = None,
) -> int | None:
    """Full months since install; increments on each install-day anniversary (not calendar month start)."""
    install = _coerce_install_date(install_date)
    if install is None:
        return None
    ref_d = ref or dt_util.as_local(dt_util.now()).date()
    if install > ref_d:
        return 0
    months = (ref_d.year - install.year) * 12 + (ref_d.month - install.month)
    if ref_d.day < install.day:
        months -= 1
    return max(0, months)


def compute_efficiency_from_install(
    install_date: str | date | None,
    annual_degradation_pct: float = 2.0,
    *,
    ref: date | None = None,
) -> int | None:
    """Solcast-style factor: 100% minus annual loss pro-rated by months since installation."""
    months = months_since_installation(install_date, ref=ref)
    if months is None:
        return None
    rate = max(0.0, min(10.0, float(annual_degradation_pct)))
    loss_pct = rate * (months / 12.0)
    efficiency = round(100 - loss_pct)
    return max(1, min(100, efficiency))


def sync_pv_efficiency_from_install(
    pv_config: PvSystemConfig,
    install_date: str | date | None,
    *,
    ref: date | None = None,
) -> tuple[PvSystemConfig, bool]:
    """Apply age-based efficiency to PV1/PV2 when an installation date is configured."""
    efficiency = compute_efficiency_from_install(
        install_date,
        pv_config.annual_degradation_pct,
        ref=ref,
    )
    if efficiency is None:
        return pv_config, False
    target = float(efficiency)
    changed = (
        int(round(pv_config.pv1.efficiency_factor)) != efficiency
        or int(round(pv_config.pv2.efficiency_factor)) != efficiency
    )
    if not changed:
        return pv_config, False
    return (
        replace(
            pv_config,
            pv1=replace(pv_config.pv1, efficiency_factor=target),
            pv2=replace(pv_config.pv2, efficiency_factor=target),
        ),
        True,
    )


def next_pv_efficiency_check(when: datetime | None = None) -> datetime:
    """Next daily local check (just after midnight) for install-anniversary age derating."""
    local = dt_util.as_local(when or dt_util.now())
    target = local.replace(hour=0, minute=15, second=0, microsecond=0)
    if local >= target:
        target += timedelta(days=1)
    return dt_util.as_utc(target)
