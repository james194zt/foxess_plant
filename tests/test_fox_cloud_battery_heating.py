"""Fox Cloud batteryHeating requests try the `sn` body key first (EVO rejects `deviceSN`)."""

from typing import Any

import pytest

from custom_components.foxess_plant.fox_cloud_api import FoxCloudApiError, FoxCloudClient


class _FakeClient(FoxCloudClient):
    """FoxCloudClient with _post replaced by a recorder; skips the HA session setup."""

    def __init__(self, reject_keys: set[str]) -> None:  # noqa: D107 — test double
        self.calls: list[dict[str, Any]] = []
        self._reject_keys = reject_keys

    async def _post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        self.calls.append(dict(body or {}))
        if any(key in (body or {}) for key in self._reject_keys):
            raise FoxCloudApiError("Parameters do not meet expectations. Please reenter", errno=40257)
        return {"dataList": [{"name": "batteryWarmUpEnable", "value": "enable"}]}


@pytest.mark.asyncio
async def test_battery_heating_get_uses_sn_first() -> None:
    client = _FakeClient(reject_keys=set())

    result = await client.get_battery_heating("SERIAL1")

    assert client.calls == [{"sn": "SERIAL1"}]
    assert result["dataList"][0]["value"] == "enable"


@pytest.mark.asyncio
async def test_battery_heating_falls_back_to_device_sn_after_40257() -> None:
    client = _FakeClient(reject_keys={"sn"})

    await client.get_battery_heating("SERIAL1")

    assert client.calls == [{"sn": "SERIAL1"}, {"deviceSN": "SERIAL1"}]


@pytest.mark.asyncio
async def test_battery_heating_set_sends_payload_with_sn() -> None:
    client = _FakeClient(reject_keys=set())

    await client.set_battery_heating("SERIAL1", {"time1Enable": "enable"})

    assert client.calls == [{"sn": "SERIAL1", "time1Enable": "enable"}]
