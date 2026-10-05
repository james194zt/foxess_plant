"""EVO SoC limit writes: write order, and Max SoC From Grid (46620) lowered before Max SoC (46610)."""

from types import SimpleNamespace

import pytest

from custom_components.foxess_plant import soc_limits

ENTITY_MAP = {
    "min_soc": "number.evo_min_soc",
    "min_soc_on_grid": "number.evo_min_soc_on_grid",
    "max_soc": "number.evo_max_soc",
    "max_soc_from_grid": "number.evo_max_soc_from_grid",
}


class _FakeEvo:
    """Number entities backed by an inverter that enforces the EVO's SoC rules."""

    def __init__(self, battery: int = 0, **values: int) -> None:
        self.battery = battery
        self.values = dict(values)
        self.writes: list[tuple[str, int]] = []
        self.states = SimpleNamespace(get=self._state)
        self.services = SimpleNamespace(async_call=self._call)

    def _key(self, entity_id: str) -> str:
        return next(key for key, eid in ENTITY_MAP.items() if eid == entity_id)

    def _state(self, entity_id: str):
        key = self._key(entity_id)
        return SimpleNamespace(state=str(self.values[key]), attributes={}) if key in self.values else None

    async def _call(self, domain: str, service: str, data: dict, blocking: bool = False) -> None:
        if (domain, service) != ("number", "set_value"):
            return
        key, value = self._key(data["entity_id"]), int(data["value"])
        new = {**self.values, key: value}
        if not new["min_soc"] <= new["min_soc_on_grid"] <= new["max_soc"]:
            raise RuntimeError("Exception Response IllegalValue")
        if new["max_soc"] < new.get("max_soc_from_grid", 0):
            raise RuntimeError("Exception Response IllegalValue")
        if key == "max_soc" and value < self.battery:  # hardware-tested: refused below the battery level
            raise RuntimeError("Exception Response IllegalValue")
        self.values = new
        self.writes.append((key, value))


@pytest.fixture(autouse=True)
def _evo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(soc_limits, "device_is_evo", lambda *args: True)
    monkeypatch.setattr(soc_limits, "resolve_uses_h3_pro_soc_block", lambda *args: True)

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(soc_limits.asyncio, "sleep", _no_sleep)


async def _apply(evo: _FakeEvo, min_soc: int, min_on_grid: int, max_soc: int) -> list[dict]:
    return await soc_limits.apply_soc_limits(
        evo, ENTITY_MAP, min_soc=min_soc, min_soc_on_grid=min_on_grid, max_soc=max_soc, force_write=True, verify=True
    )


@pytest.mark.asyncio
async def test_lowering_max_soc_lowers_max_soc_from_grid_first() -> None:
    evo = _FakeEvo(min_soc=10, min_soc_on_grid=10, max_soc=100, max_soc_from_grid=100)
    rows = await _apply(evo, 10, 10, 80)
    assert evo.writes == [("max_soc_from_grid", 80), ("max_soc", 80)]
    assert all(row["success"] for row in rows)
    assert rows[0]["label"] == "Max SOC From Grid"


@pytest.mark.asyncio
async def test_refused_max_soc_puts_max_soc_from_grid_back() -> None:
    # The battery has risen above the new max since the panel checked it
    evo = _FakeEvo(battery=60, min_soc=10, min_soc_on_grid=10, max_soc=100, max_soc_from_grid=100)
    rows = await _apply(evo, 10, 10, 50)
    assert evo.values["max_soc"] == 100
    assert evo.values["max_soc_from_grid"] == 100
    by_key = {row["key"]: row for row in rows}
    assert not by_key["max_soc"]["success"]
    assert by_key["max_soc_from_grid"]["message"].startswith("Put back")


@pytest.mark.asyncio
async def test_raising_max_soc_raises_a_tied_max_soc_from_grid() -> None:
    evo = _FakeEvo(min_soc=10, min_soc_on_grid=10, max_soc=80, max_soc_from_grid=80)
    await _apply(evo, 10, 10, 100)
    assert evo.writes == [("max_soc", 100), ("max_soc_from_grid", 100)]


@pytest.mark.asyncio
async def test_raising_max_soc_leaves_a_deliberately_lower_max_soc_from_grid() -> None:
    evo = _FakeEvo(min_soc=10, min_soc_on_grid=10, max_soc=90, max_soc_from_grid=80)
    await _apply(evo, 10, 10, 100)
    assert evo.writes == [("max_soc", 100)]


@pytest.mark.asyncio
async def test_writes_are_ordered_so_every_step_is_valid() -> None:
    # Raising system min above the current max needs max raised first
    evo = _FakeEvo(min_soc=10, min_soc_on_grid=10, max_soc=50, max_soc_from_grid=50)
    rows = await _apply(evo, 10, 60, 90)
    assert evo.values == {"min_soc": 10, "min_soc_on_grid": 60, "max_soc": 90, "max_soc_from_grid": 90}
    assert all(row["success"] for row in rows)
