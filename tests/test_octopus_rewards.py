"""Tests for Octopus rewards GraphQL parsing (no Home Assistant required)."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "foxess_plant"


def _install_ha_stubs() -> None:
    if "homeassistant.core" in sys.modules:
        return
    sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))
    for name in (
        "homeassistant",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.helpers.aiohttp_client",
    ):
        sys.modules.setdefault(name, types.ModuleType(name))
    core = sys.modules["homeassistant.core"]
    core.HomeAssistant = type("HomeAssistant", (), {})
    aiohttp_client = sys.modules["homeassistant.helpers.aiohttp_client"]
    aiohttp_client.async_get_clientsession = lambda _hass: None


def _load(name: str, rel: str):
    _install_ha_stubs()
    path = PKG / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


og = _load("octopus_graphql_test", "octopus_graphql.py")


class TestOctopusRewardsParsing(unittest.TestCase):
    def test_parse_loyalty_points_accepts_numeric_strings(self) -> None:
        self.assertEqual(og.parse_octopus_loyalty_points("1284"), 1284)
        self.assertEqual(og.parse_octopus_loyalty_points(42), 42)
        self.assertIsNone(og.parse_octopus_loyalty_points(None))
        self.assertIsNone(og.parse_octopus_loyalty_points("not-a-number"))

    def test_parse_ledger_balance_uses_first_entry(self) -> None:
        rows = [{"balanceCarriedForward": "256"}]
        self.assertEqual(og.parse_octopus_ledger_balance(rows), 256)
        self.assertIsNone(og.parse_octopus_ledger_balance([]))

    def test_parse_account_balance(self) -> None:
        self.assertEqual(og.parse_octopus_account_balance("-1250"), -1250)
        self.assertEqual(og.parse_octopus_loyalty_monetary("99"), 99)

    def test_account_user_ids(self) -> None:
        users = [{"id": "U-1"}, {"id": ""}, {"name": "missing"}]
        self.assertEqual(og.octopus_account_user_ids(users), ["U-1"])

    def test_rewards_has_data(self) -> None:
        self.assertFalse(og.octopus_rewards_has_data({}))
        self.assertFalse(
            og.octopus_rewards_has_data(
                {
                    "loyalty_points": None,
                    "loyalty_monetary_amount": None,
                    "account_balance_pence": None,
                }
            )
        )
        self.assertTrue(og.octopus_rewards_has_data({"loyalty_points": 10}))


if __name__ == "__main__":
    unittest.main()
