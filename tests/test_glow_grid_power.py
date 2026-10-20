"""Grid import/export from the Glow meter instead of the inverter CT, per direction, with a freshness guard."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from custom_components.foxess_plant.glow_grid import glow_net_power_kw, pick_grid_power_kw
from custom_components.foxess_plant.models import GlowConfig
from custom_components.foxess_plant.performance import sample

NOW = datetime(2026, 10, 20, 13, 0, tzinfo=timezone.utc)


def _live(kw, age_s):
    return {"import_kw": kw, "timestamp": (NOW - timedelta(seconds=age_s)).isoformat()}


def test_net_power_fresh_and_stale():
    assert glow_net_power_kw(_live(0.009, 10), now=NOW) == pytest.approx(0.009)
    assert glow_net_power_kw(_live(-0.5, 10), now=NOW) == pytest.approx(-0.5)
    assert glow_net_power_kw(_live(0.009, 121), now=NOW) is None  # IHD stopped publishing
    assert glow_net_power_kw({"import_kw": 0.1}, now=NOW) is None  # no timestamp, can't trust it
    assert glow_net_power_kw({"timestamp": NOW.isoformat()}, now=NOW) is None
    assert glow_net_power_kw(None, now=NOW) is None


# 20 Oct 2026 case: inverter CT said 68 W export while the meter said 9 W import.
@pytest.mark.parametrize(
    ("use_import", "use_export", "expected", "sources"),
    [
        (False, False, (0.0, 0.068), ("inverter", "inverter")),
        (True, False, (0.009, 0.068), ("glow", "inverter")),
        (False, True, (0.0, 0.0), ("inverter", "glow")),
        (True, True, (0.009, 0.0), ("glow", "glow")),
    ],
)
def test_pick_each_direction(use_import, use_export, expected, sources):
    imp, exp, src = pick_grid_power_kw(
        ct_import_kw=0.0,
        ct_export_kw=0.068,
        glow_net_kw=0.009,
        import_from_glow=use_import,
        export_from_glow=use_export,
    )
    assert (imp, exp) == pytest.approx(expected)
    assert (src["import"], src["export"]) == sources


def test_export_from_glow_when_meter_exports():
    imp, exp, _ = pick_grid_power_kw(
        ct_import_kw=0.0, ct_export_kw=2.2, glow_net_kw=-2.38, import_from_glow=True, export_from_glow=True
    )
    assert (imp, exp) == pytest.approx((0.0, 2.38))


def test_stale_glow_falls_back_to_ct():
    imp, exp, src = pick_grid_power_kw(
        ct_import_kw=0.2, ct_export_kw=0.0, glow_net_kw=None, import_from_glow=True, export_from_glow=True
    )
    assert (imp, exp) == (0.2, 0.0)
    assert src == {"import": "inverter", "export": "inverter"}


def test_config_round_trip_and_default_off():
    assert GlowConfig.from_dict({}).grid_import_from_glow is False
    assert GlowConfig.from_dict({}).grid_export_from_glow is False
    cfg = GlowConfig.from_dict({"enabled": True, "grid_import_from_glow": True, "grid_export_from_glow": True})
    again = GlowConfig.from_dict(cfg.to_dict())
    assert again.grid_import_from_glow and again.grid_export_from_glow
    public = cfg.to_dict(include_secrets=False)
    assert public["grid_import_from_glow"] is True and public["grid_export_from_glow"] is True


def _sample_net_grid(monkeypatch, glow_cfg, glow_live):
    """Performance sample grid power on a fake coordinator; CT says 68 W export."""
    ct = {"grid_import": 0.0, "grid_export": 0.068}
    monkeypatch.setattr(sample, "_entity_power_kw", lambda _c, key: ct.get(key))
    fake = SimpleNamespace(plant=SimpleNamespace(glow=glow_cfg), _glow_live=glow_live)
    imp, exp = sample._grid_power_kw(fake)
    return round((exp or 0.0) - (imp or 0.0), 3)


def test_glow_export_is_never_counted_as_import(monkeypatch):
    """Old sample code took abs() of Glow's net power, turning export into import."""
    live = {"import_kw": -0.5, "timestamp": datetime.now(timezone.utc).isoformat()}
    cfg = GlowConfig.from_dict({"enabled": True, "grid_import_from_glow": True, "grid_export_from_glow": True})
    assert _sample_net_grid(monkeypatch, cfg, live) == pytest.approx(0.5)
    off = GlowConfig.from_dict({"enabled": True})
    assert _sample_net_grid(monkeypatch, off, live) == pytest.approx(0.068)
