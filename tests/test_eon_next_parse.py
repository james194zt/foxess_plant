"""E.ON Next (Kraken) response parsing tests (no Home Assistant required)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

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


eon = _load_module("fp_eon_next_parse", "eon_next_parse.py")

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


def _point(mpan, direction, code, *, valid_to=None, product="NEXT-FLEX"):
    return {
        "mpan": mpan,
        "direction": direction,
        "agreements": [
            {
                "validFrom": "2025-01-01T00:00:00+00:00",
                "validTo": "2026-01-01T00:00:00+00:00",
                "tariff": {"tariffCode": "E-1R-OLD-A", "productCode": "OLD", "displayName": "Old"},
            },
            {
                "validFrom": "2026-01-01T00:00:00+00:00",
                "validTo": valid_to,
                "tariff": {"tariffCode": code, "productCode": product, "displayName": "Next Flex"},
            },
        ],
    }


class MetersFromAccountsTests(unittest.TestCase):
    def test_split_import_and_export_accounts(self) -> None:
        accounts = [
            {"number": "a-111", "properties": [{"electricityMeterPoints": [_point("100", "IMPORT", "E-1R-NEXT-FLEX-A")]}]},
            {"number": "A-222", "properties": [{"electricityMeterPoints": [_point("200", "EXPORT", "E-1R-NEXT-EXPORT-A")]}]},
        ]
        imports, exports = eon.meters_from_accounts(accounts, now=NOW)
        self.assertEqual([m["mpan"] for m in imports], ["100"])
        self.assertEqual([m["mpan"] for m in exports], ["200"])
        self.assertEqual(imports[0]["account_number"], "A-111")
        self.assertEqual(exports[0]["account_number"], "A-222")
        # The expired 2025 agreement must not win over the current one.
        self.assertEqual(imports[0]["tariff_code"], "E-1R-NEXT-FLEX-A")
        self.assertEqual(imports[0]["product_code"], "NEXT-FLEX")

    def test_direction_missing_falls_back_to_tariff_code(self) -> None:
        accounts = [{"number": "A-1", "properties": [{"electricityMeterPoints": [
            _point("1", None, "E-1R-NEXT-FLEX-A"),
            _point("2", "", "E-1R-NEXT-EXPORT-FIXED-A"),
        ]}]}]
        imports, exports = eon.meters_from_accounts(accounts, now=NOW)
        self.assertEqual([m["mpan"] for m in imports], ["1"])
        self.assertEqual([m["mpan"] for m in exports], ["2"])

    def test_no_active_agreement_leaves_tariff_empty(self) -> None:
        accounts = [{"number": "A-1", "properties": [{"electricityMeterPoints": [
            _point("1", "IMPORT", "E-1R-X-A", valid_to="2026-02-01T00:00:00Z"),
        ]}]}]
        imports, _ = eon.meters_from_accounts(accounts, now=NOW)
        self.assertIsNone(imports[0]["tariff_code"])


class PickMeterTests(unittest.TestCase):
    meters = [
        {"account_number": "A-1", "mpan": "1", "tariff_code": "X", "is_export": False},
        {"account_number": "A-2", "mpan": "2", "tariff_code": "Y", "is_export": False},
    ]

    def test_configured_mpan(self) -> None:
        self.assertEqual(eon.pick_meter(self.meters, "2", role="import")["mpan"], "2")

    def test_unknown_mpan_raises(self) -> None:
        with self.assertRaises(ValueError):
            eon.pick_meter(self.meters, "9", role="import")

    def test_ambiguous_without_preference_raises(self) -> None:
        with self.assertRaises(ValueError):
            eon.pick_meter(self.meters, None, role="import")

    def test_preferred_account_resolves_ambiguity(self) -> None:
        self.assertEqual(
            eon.pick_meter(self.meters, None, role="import", preferred_account="a-2")["mpan"], "2"
        )

    def test_empty_export_is_none(self) -> None:
        self.assertIsNone(eon.pick_meter([], None, role="export", allow_first=True))


class RateRowTests(unittest.TestCase):
    def test_flat_rest_row_gets_open_start(self) -> None:
        rows = eon.normalize_rest_rows(
            [{"value_inc_vat": 24.5, "valid_from": None, "valid_to": None}, {"value_inc_vat": None}]
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["valid_from"], eon.OPEN_START_ISO)
        self.assertIsNone(rows[0]["valid_to"])

    def test_graphql_connection_to_rows(self) -> None:
        rows = eon.graphql_nodes_to_rows(
            {"edges": [
                {"node": {"value": "7.5", "validFrom": "2026-09-27T23:00:00Z", "validTo": "2026-09-28T06:00:00Z"}},
                {"node": {"value": None}},
            ]}
        )
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["value_inc_vat"], 7.5)
        self.assertAlmostEqual(rows[0]["value_exc_vat"], round(7.5 / 1.05, 4))
        self.assertEqual(rows[0]["valid_from"], "2026-09-27T23:00:00Z")


class ClassifyTests(unittest.TestCase):
    def test_classify(self) -> None:
        self.assertEqual(eon.classify_eon_tariff_code("E-TOU-NEXT-DRIVE-SMART-V1-A"), "go")
        self.assertEqual(eon.classify_eon_tariff_code("E-2R-NEXT-FLEX-A"), "economy7")
        self.assertEqual(eon.classify_eon_tariff_code("E-1R-NEXT-FIXED-12M-A"), "flat")
        self.assertEqual(eon.classify_eon_tariff_code(None), "flat")


class ErrorTests(unittest.TestCase):
    def test_error_message_includes_code(self) -> None:
        errors = [{"message": "Invalid data.", "extensions": {"errorCode": "KT-CT-1138"}}]
        self.assertEqual(eon.graphql_error_code(errors), "KT-CT-1138")
        self.assertEqual(eon.graphql_error_message(errors), "Invalid data. (KT-CT-1138)")



class TokenHelperTests(unittest.TestCase):
    def test_clean_pasted_token_strips_quotes_and_space(self) -> None:
        self.assertEqual(eon.clean_pasted_token('  "v1.abc"  '), "v1.abc")
        self.assertEqual(eon.clean_pasted_token("'v1.abc'"), "v1.abc")
        self.assertEqual(eon.clean_pasted_token(None), "")

    def test_token_seed_is_stable_and_not_the_token(self) -> None:
        seed = eon.token_seed("v1.secret")
        self.assertEqual(seed, eon.token_seed("v1.secret"))
        self.assertNotIn("secret", seed)
        self.assertNotEqual(seed, eon.token_seed("v1.other"))
        self.assertEqual(eon.token_seed(""), "")

    def test_jwt_exp(self) -> None:
        import base64
        import json

        part = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
        token = f"{part({'alg': 'RS256'})}.{part({'exp': 1790000000})}.sig"
        self.assertEqual(eon.jwt_exp(token), 1790000000.0)
        self.assertIsNone(eon.jwt_exp("opaque-access-token"))
        self.assertIsNone(eon.jwt_exp("a.!!!.c"))


if __name__ == "__main__":
    unittest.main()
