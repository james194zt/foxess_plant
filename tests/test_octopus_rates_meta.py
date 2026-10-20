"""The Octopus client keeps the evidence of each unit-rates request (for plunge_evidence.py)."""

import json

import pytest

from custom_components.foxess_plant.octopus_api import OctopusApiClient

ROWS = [{"value_exc_vat": -2.0, "value_inc_vat": -2.1, "valid_from": "2026-10-20T13:00:00Z", "valid_to": "2026-10-20T13:30:00Z"}]


class _Resp:
    status = 200
    headers = {"Date": "Mon, 20 Oct 2026 12:00:01 GMT"}

    async def text(self):
        return json.dumps({"count": 1, "next": None, "results": ROWS})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _Session:
    def __init__(self):
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        assert "key" not in url.lower()  # the API key only goes in Basic auth
        return _Resp()


@pytest.mark.asyncio
async def test_unit_rates_keep_url_time_status_and_server_date(hass) -> None:
    client = OctopusApiClient(hass, api_key="sk_live_secret")
    client._session = _Session()

    rows = await client.get_unit_rates("AGILE-24-10-01", "E-1R-AGILE-24-10-01-C", period_from="2026-10-20T10:00:00Z")

    assert rows == ROWS
    meta = client.rates_meta["E-1R-AGILE-24-10-01-C"]
    assert meta["url"].startswith("https://api.octopus.energy/v1/products/AGILE-24-10-01/")
    assert "period_from=2026-10-20T10" in meta["url"]
    assert meta["server_date"] == "Mon, 20 Oct 2026 12:00:01 GMT"
    assert meta["http_status"] == 200
    assert meta["requested_at"]
    assert meta["rows"] == 1
    assert "sk_live_secret" not in json.dumps(meta)
