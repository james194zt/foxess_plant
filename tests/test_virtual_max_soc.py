"""Unit tests for virtual max SOC cap resolution."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = REPO_ROOT / "custom_components" / "foxess_plant"


def _load_module(name: str, relative: str):
    path = PKG_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


virtual_max_soc = _load_module("virtual_max_soc_test", "virtual_max_soc.py")


def _coordinator(
    *,
    storm_active: bool = False,
    storm_target: float | None = None,
    sc_enabled: bool = False,
    sc_target_max: float | None = None,
    sc_max_target: float = 90.0,
    virtual_quick: int | None = None,
    control_active: bool = True,
    entity_max: float | None = None,
):
    plant = SimpleNamespace(
        storm_prep=SimpleNamespace(target_max_soc=storm_target),
        smart_charge=SimpleNamespace(
            enabled=sc_enabled,
            target_max_soc=sc_target_max,
            max_target_soc=sc_max_target,
        ),
        virtual_soc=SimpleNamespace(max_soc=virtual_quick),
        control_active=control_active,
    )
    coord = SimpleNamespace(
        plant=plant,
        _active_storm_triggers={"storm"} if storm_active else set(),
        _entity_float=MagicMock(return_value=entity_max),
    )
    return coord


class VirtualMaxSocTests(unittest.TestCase):
    def test_storm_overrides_smart_charge(self) -> None:
        cap, source = virtual_max_soc.resolve_virtual_max_soc_cap(
            _coordinator(
                storm_active=True,
                storm_target=100.0,
                sc_enabled=True,
                sc_max_target=80.0,
                virtual_quick=70,
            )
        )
        self.assertEqual(cap, 100.0)
        self.assertEqual(source, virtual_max_soc.CAP_SOURCE_STORM)

    def test_smart_charge_overrides_quick(self) -> None:
        cap, source = virtual_max_soc.resolve_virtual_max_soc_cap(
            _coordinator(sc_enabled=True, sc_max_target=85.0, virtual_quick=70)
        )
        self.assertEqual(cap, 85.0)
        self.assertEqual(source, virtual_max_soc.CAP_SOURCE_SMART_CHARGE)

    def test_smart_charge_uses_target_max_when_set(self) -> None:
        cap, _ = virtual_max_soc.resolve_virtual_max_soc_cap(
            _coordinator(sc_enabled=True, sc_target_max=78.0, sc_max_target=95.0)
        )
        self.assertEqual(cap, 78.0)

    def test_quick_virtual_when_sc_off(self) -> None:
        cap, source = virtual_max_soc.resolve_virtual_max_soc_cap(
            _coordinator(virtual_quick=72, sc_enabled=False)
        )
        self.assertEqual(cap, 72.0)
        self.assertEqual(source, virtual_max_soc.CAP_SOURCE_QUICK)

    def test_pick_feed_in_work_mode(self) -> None:
        self.assertEqual(
            virtual_max_soc.pick_feed_in_work_mode(["Self Use", "Feed-in Priority"]),
            "Feed-in Priority",
        )
        self.assertEqual(
            virtual_max_soc.pick_feed_in_work_mode(["Feed-in First"]),
            "Feed-in First",
        )


if __name__ == "__main__":
    unittest.main()
