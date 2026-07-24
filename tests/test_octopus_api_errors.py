"""Unit tests for Octopus HTTP error summarisation."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = REPO_ROOT / "custom_components" / "foxess_plant"


def _load_module(name: str, relative: str):
    path = PKG_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    import types

    if "homeassistant" not in sys.modules:
        ha = types.ModuleType("homeassistant")
        ha_core = types.ModuleType("homeassistant.core")
        ha_core.HomeAssistant = object
        ha_helpers = types.ModuleType("homeassistant.helpers")
        ha_aio = types.ModuleType("homeassistant.helpers.aiohttp_client")
        ha_aio.async_get_clientsession = lambda hass: None
        ha.core = ha_core
        ha.helpers = ha_helpers
        ha_helpers.aiohttp_client = ha_aio
        sys.modules["homeassistant"] = ha
        sys.modules["homeassistant.core"] = ha_core
        sys.modules["homeassistant.helpers"] = ha_helpers
        sys.modules["homeassistant.helpers.aiohttp_client"] = ha_aio
        aiohttp = types.ModuleType("aiohttp")
        aiohttp.BasicAuth = object
        aiohttp.ClientError = Exception
        aiohttp.ClientTimeout = lambda **kwargs: None
        sys.modules["aiohttp"] = aiohttp
    spec.loader.exec_module(module)
    return module


octopus_api = _load_module("foxess_octopus_api", "octopus_api.py")


class OctopusErrorSummaryTests(unittest.TestCase):
    def test_html_500_is_human_readable(self) -> None:
        msg = octopus_api.summarise_octopus_http_error(
            500,
            "<!doctype html><html><title>Server Error (500)</title></html>",
        )
        self.assertIn("temporary server error", msg)
        self.assertNotIn("<!doctype", msg.lower())

    def test_json_detail_preserved(self) -> None:
        msg = octopus_api.summarise_octopus_http_error(401, '{"detail":"Invalid API key."}')
        self.assertIn("Invalid API key", msg)


if __name__ == "__main__":
    unittest.main()
