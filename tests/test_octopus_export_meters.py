"""Tests for Octopus export meter discovery helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "foxess_plant"
PKG_NAME = "custom_components.foxess_plant"


def _install_ha_stubs() -> None:
    for name in (
        "homeassistant",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.util",
        "homeassistant.util.dt",
    ):
        sys.modules.setdefault(name, types.ModuleType(name))
    dt = sys.modules["homeassistant.util.dt"]
    dt.as_local = lambda value: value
    dt.as_utc = lambda value: value
    dt.utcnow = lambda: datetime.now(timezone.utc)
    dt.now = lambda tz=None: datetime.now(tz or timezone.utc)
    dt.parse_datetime = lambda raw: datetime.fromisoformat(str(raw).replace("Z", "+00:00"))


def _ensure_pkg() -> None:
    sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
    if PKG_NAME not in sys.modules:
        pkg = types.ModuleType(PKG_NAME)
        pkg.__path__ = [str(PKG)]
        sys.modules[PKG_NAME] = pkg


def _stub_sub(mod_name: str, **attrs):
    _ensure_pkg()
    full = f"{PKG_NAME}.{mod_name}"
    stub = types.ModuleType(full)
    for key, value in attrs.items():
        setattr(stub, key, value)
    sys.modules[full] = stub
    return stub


_install_ha_stubs()
_stub_sub("octopus_api", OctopusApiClient=type("OctopusApiClient", (), {}), OctopusApiError=Exception)
_stub_sub(
    "tariff_schedule",
    TARIFF_BAND_COUNT=4,
    TARIFF_HOUR_COUNT=24,
    TariffBandConfig=type("TariffBandConfig", (), {}),
    TariffScheduleConfig=type("TariffScheduleConfig", (), {"to_dict": lambda self: {}}),
)
_ensure_pkg()
_spec = importlib.util.spec_from_file_location(
    f"{PKG_NAME}.octopus_tariff", PKG / "octopus_tariff.py"
)
ot = importlib.util.module_from_spec(_spec)
sys.modules[f"{PKG_NAME}.octopus_tariff"] = ot
_spec.loader.exec_module(ot)


class TestExportMeterDetection(unittest.TestCase):
    def test_tariff_looks_like_export(self):
        self.assertTrue(ot.tariff_looks_like_export("E-1R-AGILE-OUTGOING-BB-23-02-28-J"))
        self.assertTrue(ot.tariff_looks_like_export("E-1R-OUTGOING-FIX-12M-23-09-12-A"))
        self.assertTrue(ot.tariff_looks_like_export("E-1R-SEG-HH-1234-A"))
        self.assertTrue(ot.tariff_looks_like_export("E-1R-FLUX-EXPORT-23-02-14-A"))
        self.assertFalse(ot.tariff_looks_like_export("E-1R-AGILE-24-10-01-A"))
        self.assertFalse(ot.tariff_looks_like_export("E-1R-FLUX-IMPORT-23-02-14-A"))

    def test_list_account_meters_detects_outgoing_without_is_export_flag(self):
        now = datetime.now(timezone.utc)
        account = {
            "properties": [
                {
                    "electricity_meter_points": [
                        {
                            "mpan": "1111111111111",
                            "is_export": False,
                            "meters": [{"serial_number": "IMP001"}],
                            "agreements": [
                                {
                                    "tariff_code": "E-1R-AGILE-24-10-01-A",
                                    "valid_from": (now - timedelta(days=30)).isoformat(),
                                    "valid_to": None,
                                }
                            ],
                        },
                        {
                            "mpan": "2222222222222",
                            "is_export": False,
                            "meters": [{"serial_number": "EXP001"}],
                            "agreements": [
                                {
                                    "tariff_code": "E-1R-AGILE-OUTGOING-BB-23-02-28-J",
                                    "valid_from": (now - timedelta(days=30)).isoformat(),
                                    "valid_to": None,
                                }
                            ],
                        },
                    ]
                }
            ]
        }
        imports, exports = ot.list_account_meters(account)
        self.assertEqual(len(imports), 1)
        self.assertEqual(len(exports), 1)
        self.assertEqual(exports[0].mpan, "2222222222222")
        self.assertEqual(exports[0].serial, "EXP001")

    def test_merge_export_meters_fills_missing_serial(self):
        rest = [
            ot.OctopusMeterSummary(
                mpan="2222222222222",
                serial=None,
                is_export=True,
                tariff_code="E-1R-OUTGOING-FIX-12M-23-09-12-A",
                product_code=None,
                display_name="2222",
            )
        ]
        gql = [
            ot.OctopusMeterSummary(
                mpan="2222222222222",
                serial="EXP999",
                is_export=True,
                tariff_code="E-1R-OUTGOING-FIX-12M-23-09-12-A",
                product_code=None,
                display_name="2222",
            )
        ]
        merged = ot.merge_export_meters(rest, gql)
        self.assertEqual(merged[0].serial, "EXP999")

    def test_resolve_meter_for_consumption_from_meters_list(self):
        cache = {
            "export_meter": {"mpan": "2222222222222", "serial": None},
            "export_meters": [{"mpan": "2222222222222", "serial": "EXP001"}],
        }
        meter = ot.resolve_meter_for_consumption(cache, export=True)
        self.assertEqual(meter.get("serial"), "EXP001")

    def test_pick_serial_skips_closed_meter(self):
        now = datetime.now(timezone.utc)
        serial = ot._pick_serial_from_meters(
            [
                {
                    "serial_number": "OLD",
                    "active_to": (now - timedelta(days=1)).isoformat(),
                },
                {"serial_number": "NEW"},
            ],
            now=now,
        )
        self.assertEqual(serial, "NEW")


if __name__ == "__main__":
    unittest.main()
