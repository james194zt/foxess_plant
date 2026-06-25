"""TEMPORARY — Modbus scheduler capability probe for EVO validation.

Delete this module and search ``DEBUG_MODBUS_PROBE`` in the repo to remove all wiring.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .charge_period import apply_charge_periods
from .const import CHARGE_PERIOD_KEYS, MODBUS_DOMAIN
from .models import ChargePeriodConfig
from .entity_live import async_poll_entity_id_live, async_poll_entity_key_live, async_read_soc_live
from .remote_control import set_remote_control_mode
from .soc_limits import apply_soc_limits, read_soc_current

_LOGGER = logging.getLogger(__name__)

_PROBE_REFRESH_SLEEP_S = 0.5
_POLL_INTERVAL_S = 2.0
_WRITE_SETTLE_POLL_TIMEOUT_S = 30.0


@dataclass
class _RestoreAction:
    label: str
    action: Callable[[], Coroutine[Any, Any, None]]


@dataclass
class _ProbeContext:
    hass: HomeAssistant
    inverter_ref: str
    entity_map: dict[str, str]
    device_id: str
    results: list[dict[str, Any]] = field(default_factory=list)
    restore: list[_RestoreAction] = field(default_factory=list)

    def entity_state(self, key: str) -> str | None:
        entity_id = self.entity_map.get(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        return state.state if state else None

    def entity_options(self, key: str) -> list[str]:
        entity_id = self.entity_map.get(key)
        if not entity_id:
            return []
        state = self.hass.states.get(entity_id)
        if not state:
            return []
        options = state.attributes.get("options")
        return list(options) if isinstance(options, list) else []

    def add_result(
        self,
        *,
        test_id: str,
        name: str,
        status: str,
        write_ok: bool | None = None,
        read_back_ok: bool | None = None,
        before: Any = None,
        attempted: Any = None,
        after: Any = None,
        error: str | None = None,
        notes: str | None = None,
    ) -> None:
        self.results.append(
            {
                "id": test_id,
                "name": name,
                "status": status,
                "write_ok": write_ok,
                "read_back_ok": read_back_ok,
                "before": before,
                "attempted": attempted,
                "after": after,
                "error": error,
                "notes": notes,
            }
        )

    async def refresh_keys(self, keys: tuple[str, ...] | list[str]) -> None:
        tasks = []
        for key in keys:
            entity_id = self.entity_map.get(key)
            if entity_id:
                tasks.append(
                    self.hass.services.async_call(
                        "homeassistant",
                        "update_entity",
                        {"entity_id": entity_id},
                        blocking=True,
                    )
                )
        if tasks:
            await asyncio.gather(*tasks)
            await asyncio.sleep(_PROBE_REFRESH_SLEEP_S)


def _timing_note(elapsed_s: float, attempts: int, *, delayed: bool = False) -> str:
    prefix = "Delayed read-back after" if delayed else "Read-back after"
    return f"{prefix} {elapsed_s:.1f}s ({attempts} check(s), up to {_WRITE_SETTLE_POLL_TIMEOUT_S:.0f}s settle)."


async def _poll_entity_key(
    ctx: _ProbeContext,
    key: str,
    *,
    expected: str | Callable[[str | None], bool],
    timeout_s: float = _WRITE_SETTLE_POLL_TIMEOUT_S,
) -> tuple[bool, str | None, float, int]:
    return await async_poll_entity_key_live(
        ctx.hass,
        ctx.entity_map,
        key,
        expected=expected,
        timeout_s=timeout_s,
        poll_interval_s=_POLL_INTERVAL_S,
    )


async def _poll_soc_values(
    ctx: _ProbeContext,
    target: dict[str, int],
    *,
    keys: tuple[str, ...] = ("min_soc", "min_soc_on_grid", "max_soc"),
    timeout_s: float = _WRITE_SETTLE_POLL_TIMEOUT_S,
) -> tuple[bool, dict[str, int], float, int]:
    loop = asyncio.get_running_loop()
    start = loop.time()
    attempts = 0
    final: dict[str, int] = {}
    while True:
        attempts += 1
        await ctx.refresh_keys(keys)
        final = read_soc_current(ctx.hass, ctx.entity_map)
        matched = all(final.get(key) == target.get(key) for key in keys if key in target)
        if matched:
            return True, final, loop.time() - start, attempts
        if loop.time() - start >= timeout_s:
            return False, final, loop.time() - start, attempts
        await asyncio.sleep(_POLL_INTERVAL_S)


async def _poll_holding_register(
    hass: HomeAssistant,
    inverter_ref: str,
    address: int,
    expected: int,
    *,
    timeout_s: float = _WRITE_SETTLE_POLL_TIMEOUT_S,
) -> tuple[bool, int | None, float, int, str | None]:
    loop = asyncio.get_running_loop()
    start = loop.time()
    attempts = 0
    final: int | None = None
    last_err: str | None = None
    while True:
        attempts += 1
        values, err = await _read_holding(hass, inverter_ref, address, 1)
        last_err = err
        final = values.get(address) if values else None
        if err is None and final == expected:
            return True, final, loop.time() - start, attempts, None
        if loop.time() - start >= timeout_s:
            return False, final, loop.time() - start, attempts, last_err
        await asyncio.sleep(_POLL_INTERVAL_S)


async def _settle_then_read_holding(
    hass: HomeAssistant,
    inverter_ref: str,
    address: int,
) -> tuple[int | None, float, str | None]:
    """Single read after full settle window (for writes that failed immediately)."""
    await asyncio.sleep(_WRITE_SETTLE_POLL_TIMEOUT_S)
    values, err = await _read_holding(hass, inverter_ref, address, 1)
    return (values.get(address) if values else None), _WRITE_SETTLE_POLL_TIMEOUT_S, err


async def _poll_charge_period_1(
    ctx: _ProbeContext,
    expected: ChargePeriodConfig,
    *,
    timeout_s: float = _WRITE_SETTLE_POLL_TIMEOUT_S,
) -> tuple[bool, dict[str, Any], float, int]:
    loop = asyncio.get_running_loop()
    start = loop.time()
    attempts = 0
    after = _read_period(ctx, 1)
    while True:
        attempts += 1
        await ctx.refresh_keys(CHARGE_PERIOD_KEYS)
        after = _read_period(ctx, 1)
        read_ok = expected.matches_modbus_state(
            after["enable_force_charge"],
            after["enable_charge_from_grid"],
            after.get("start"),
            after.get("end"),
        )
        if read_ok:
            return True, after, loop.time() - start, attempts
        if loop.time() - start >= timeout_s:
            return False, after, loop.time() - start, attempts
        await asyncio.sleep(_POLL_INTERVAL_S)


def _find_entity_by_suffix(hass: HomeAssistant, device_id: str, suffix: str) -> str | None:
    reg = er.async_get(hass)
    for entry in reg.entities.values():
        if entry.device_id == device_id and entry.entity_id.endswith(f"_{suffix}"):
            return entry.entity_id
    return None


async def _read_holding(
    hass: HomeAssistant,
    inverter_ref: str,
    start_address: int,
    count: int,
) -> tuple[dict[int, int] | None, str | None]:
    try:
        response = await hass.services.async_call(
            MODBUS_DOMAIN,
            "read_registers",
            {
                "inverter": inverter_ref,
                "start_address": start_address,
                "count": count,
                "type": "holding",
            },
            blocking=True,
            return_response=True,
        )
    except Exception as err:
        return None, str(err)
    if not isinstance(response, dict):
        return None, "No response from read_registers"
    if response.get("error"):
        return None, str(response["error"])
    values = response.get("values") or {}
    return {int(k): int(v) for k, v in values.items()}, None


def _normalize_period_time(value: str | None) -> str | None:
    if not value or value in ("unknown", "unavailable"):
        return None
    parts = str(value).split(":")
    if len(parts) >= 2:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    return str(value)


def _read_period(ctx: _ProbeContext, index: int) -> dict[str, Any]:
    prefix = f"time_period_{index}"
    force = ctx.entity_state(f"{prefix}_enable_force_charge")
    grid = ctx.entity_state(f"{prefix}_enable_charge_from_grid")
    return {
        "enable_force_charge": force in ("on", "true", "1"),
        "enable_charge_from_grid": grid in ("on", "true", "1"),
        "start": _normalize_period_time(ctx.entity_state(f"{prefix}_start")),
        "end": _normalize_period_time(ctx.entity_state(f"{prefix}_end")),
    }


def _period_to_config(data: dict[str, Any]) -> ChargePeriodConfig:
    return ChargePeriodConfig(
        enable_force_charge=bool(data.get("enable_force_charge")),
        enable_charge_from_grid=bool(data.get("enable_charge_from_grid")),
        start=str(data.get("start") or "00:00"),
        end=str(data.get("end") or "00:00"),
    )


async def _run_restore(ctx: _ProbeContext) -> None:
    for item in reversed(ctx.restore):
        try:
            await item.action()
        except Exception as err:
            _LOGGER.warning("Modbus probe restore %s failed: %s", item.label, err)


async def _test_register_reads(ctx: _ProbeContext) -> None:
    blocks = (
        ("read_48000_block", "Read holding 48000–48013", 48000, 14),
        ("read_48020_block", "Read holding 48020–48023", 48020, 4),
        ("read_soc_registers", "Read holding 46609–46611 (SOC)", 46609, 3),
    )
    for test_id, name, start, count in blocks:
        values, err = await _read_holding(ctx.hass, ctx.inverter_ref, start, count)
        if err:
            ctx.add_result(
                test_id=test_id,
                name=name,
                status="fail",
                error=err,
                notes="Raw Modbus read failed — register may be absent or gateway blocked.",
            )
            continue
        ctx.add_result(
            test_id=test_id,
            name=name,
            status="pass",
            read_back_ok=True,
            after=values,
            notes=f"Read {len(values or {})} register(s).",
        )


async def _test_entity_snapshot(ctx: _ProbeContext) -> None:
    keys = (
        "work_mode",
        "remote_control",
        "min_soc",
        "min_soc_on_grid",
        "max_soc",
        *CHARGE_PERIOD_KEYS,
    )
    await ctx.refresh_keys(keys)
    snapshot = {key: ctx.entity_state(key) for key in keys}
    missing = [key for key in keys if snapshot.get(key) in (None, "unknown", "unavailable")]
    ctx.add_result(
        test_id="entity_snapshot",
        name="Entity snapshot (before writes)",
        status="warn" if missing else "pass",
        read_back_ok=not missing,
        after=snapshot,
        notes=f"Missing/unavailable: {', '.join(missing)}" if missing else "All scheduler entities readable.",
    )


async def _test_work_mode(ctx: _ProbeContext) -> None:
    entity_id = ctx.entity_map.get("work_mode")
    if not entity_id:
        ctx.add_result(
            test_id="work_mode_write",
            name="Work mode write + live read-back",
            status="skip",
            notes="work_mode entity not mapped.",
        )
        return
    await ctx.refresh_keys(("work_mode",))
    before = await async_read_entity_key_live(ctx.hass, ctx.entity_map, "work_mode")
    options = ctx.entity_options("work_mode")
    target = next((opt for opt in options if opt != before), None)
    if not target:
        ctx.add_result(
            test_id="work_mode_write",
            name="Work mode write + live read-back",
            status="skip",
            before=before,
            notes="No alternate work mode option to test with.",
        )
        return

    write_err: str | None = None
    try:
        await ctx.hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": target},
            blocking=True,
        )
    except Exception as err:
        write_err = str(err)

    read_ok = False
    after: str | None = None
    poll_s = 0.0
    poll_attempts = 0
    if write_err is None:
        read_ok, after, poll_s, poll_attempts = await _poll_entity_key(
            ctx,
            "work_mode",
            expected=target,
        )
    timing_note = (
        f"{_timing_note(poll_s, poll_attempts)} Refreshed entity from inverter before each check."
        if write_err is None
        else None
    )
    ctx.add_result(
        test_id="work_mode_write",
        name="Work mode write + live read-back",
        status="pass" if write_err is None and read_ok else "fail",
        write_ok=write_err is None,
        read_back_ok=read_ok,
        before=before,
        attempted=target,
        after=after,
        error=write_err,
        notes=timing_note,
    )

    if write_err is None:
        saved = before

        async def _restore() -> None:
            await ctx.hass.services.async_call(
                "select",
                "select_option",
                {"entity_id": entity_id, "option": saved},
                blocking=True,
            )
            await _poll_entity_key(ctx, "work_mode", expected=saved)

        ctx.restore.append(_RestoreAction("work_mode", _restore))


async def _test_soc_limits(ctx: _ProbeContext) -> None:
    await ctx.refresh_keys(("min_soc", "min_soc_on_grid", "max_soc"))
    before = read_soc_current(ctx.hass, ctx.entity_map)
    if len(before) < 2:
        ctx.add_result(
            test_id="soc_limits_write",
            name="SOC limits write + read-back",
            status="skip",
            before=before,
            notes="Need min_soc and min_soc_on_grid entities.",
        )
        return

    min_v = before.get("min_soc", 10)
    mid_v = before.get("min_soc_on_grid", min_v)
    max_v = before.get("max_soc", 100)
    bump = 1 if min_v < min(mid_v, max_v) else (-1 if min_v > 10 else 0)
    if bump == 0:
        ctx.add_result(
            test_id="soc_limits_write",
            name="SOC limits write + read-back",
            status="skip",
            before=before,
            notes="Could not pick a safe alternate min_soc value.",
        )
        return

    target_min = min_v + bump
    target = {"min_soc": target_min, "min_soc_on_grid": mid_v, "max_soc": max_v}

    write_err: str | None = None
    rows: list[dict[str, Any]] = []
    try:
        rows = await apply_soc_limits(
            ctx.hass,
            ctx.entity_map,
            min_soc=target_min,
            min_soc_on_grid=mid_v,
            max_soc=max_v,
            force_write=True,
            verify=False,
            emulate_max_soc=True,
        )
    except Exception as err:
        write_err = str(err)

    poll_s = 0.0
    poll_attempts = 0
    read_ok = False
    after = before
    if write_err is None:
        read_ok, after, poll_s, poll_attempts = await _poll_soc_values(
            ctx,
            {"min_soc": target_min},
            keys=("min_soc",),
        )
    max_row = next((row for row in rows if row.get("key") == "max_soc"), None)
    notes: list[str] = []
    if write_err is None:
        notes.append(_timing_note(poll_s, poll_attempts))
    if max_row and max_row.get("skipped"):
        notes.append(str(max_row.get("message") or "max_soc skipped (EVO virtual cap path)."))

    ctx.add_result(
        test_id="soc_limits_write",
        name="SOC limits write + read-back (min_soc bump)",
        status="pass" if write_err is None and read_ok else "fail",
        write_ok=write_err is None,
        read_back_ok=read_ok,
        before=before,
        attempted=target,
        after=after,
        error=write_err,
        notes=" ".join(notes) if notes else None,
    )

    if write_err is None:

        async def _restore() -> None:
            await apply_soc_limits(
                ctx.hass,
                ctx.entity_map,
                min_soc=before.get("min_soc", min_v),
                min_soc_on_grid=before.get("min_soc_on_grid", mid_v),
                max_soc=before.get("max_soc", max_v),
                force_write=True,
                verify=False,
                emulate_max_soc=True,
            )
            await _poll_soc_values(
                ctx,
                {
                    "min_soc": before.get("min_soc", min_v),
                    "min_soc_on_grid": before.get("min_soc_on_grid", mid_v),
                    "max_soc": before.get("max_soc", max_v),
                },
            )

        ctx.restore.append(_RestoreAction("soc_limits", _restore))


async def _test_remote_control(ctx: _ProbeContext) -> None:
    await ctx.refresh_keys(("remote_control",))
    before = ctx.entity_state("remote_control")
    if before not in (None, "Disable", "unknown", "unavailable", ""):
        ctx.add_result(
            test_id="remote_control_write",
            name="Remote Control Force Charge + read-back",
            status="skip",
            before=before,
            notes="Remote Control already active — set to Disable first, then re-run.",
        )
        return

    write_err: str | None = None
    try:
        await set_remote_control_mode(ctx.hass, ctx.entity_map, "Force Charge")
    except Exception as err:
        write_err = str(err)

    read_ok = False
    after: str | None = None
    poll_s = 0.0
    poll_attempts = 0
    if write_err is None:
        read_ok, after, poll_s, poll_attempts = await _poll_entity_key(
            ctx,
            "remote_control",
            expected="Force Charge",
        )
    ctx.add_result(
        test_id="remote_control_write",
        name="Remote Control Force Charge + read-back",
        status="pass" if write_err is None and read_ok else "fail",
        write_ok=write_err is None,
        read_back_ok=read_ok,
        before=before,
        attempted="Force Charge",
        after=after,
        error=write_err,
        notes=_timing_note(poll_s, poll_attempts) if write_err is None else None,
    )

    restore_mode = before if before not in (None, "unknown", "unavailable", "") else "Disable"

    async def _restore() -> None:
        await set_remote_control_mode(ctx.hass, ctx.entity_map, restore_mode)
        await _poll_entity_key(ctx, "remote_control", expected=restore_mode)

    ctx.restore.append(_RestoreAction("remote_control", _restore))


async def _test_charge_period(ctx: _ProbeContext) -> None:
    await ctx.refresh_keys(CHARGE_PERIOD_KEYS)
    before_p1 = _read_period(ctx, 1)
    before_p2 = _read_period(ctx, 2)
    test_p1 = ChargePeriodConfig(
        enable_force_charge=True,
        enable_charge_from_grid=True,
        start="23:00",
        end="23:50",
    )
    periods = [test_p1, _period_to_config(before_p2)]

    write_err: str | None = None
    try:
        await apply_charge_periods(
            ctx.hass,
            ctx.inverter_ref,
            periods,
            entity_map=ctx.entity_map,
        )
    except Exception as err:
        write_err = str(err)

    poll_s = 0.0
    poll_attempts = 0
    read_ok = False
    after_p1 = before_p1
    notes = ["Uses foxess_modbus.update_all_charge_periods (480xx path)."]
    if write_err is None:
        read_ok, after_p1, poll_s, poll_attempts = await _poll_charge_period_1(ctx, test_p1)
        notes.append(_timing_note(poll_s, poll_attempts))
    else:
        await asyncio.sleep(_WRITE_SETTLE_POLL_TIMEOUT_S)
        poll_s = _WRITE_SETTLE_POLL_TIMEOUT_S
        poll_attempts = 1
        await ctx.refresh_keys(CHARGE_PERIOD_KEYS)
        after_p1 = _read_period(ctx, 1)
        read_ok = test_p1.matches_modbus_state(
            after_p1["enable_force_charge"],
            after_p1["enable_charge_from_grid"],
            after_p1.get("start"),
            after_p1.get("end"),
        )
        notes.append(
            _timing_note(poll_s, poll_attempts, delayed=True)
            + " Write returned an error; checked entities after settle anyway."
        )
        if read_ok:
            notes.append(
                "Charge period entities changed despite write error — may be slow Modbus, not IllegalAddress."
            )

    if read_ok and write_err is None:
        status = "pass"
    elif read_ok and write_err:
        status = "warn"
    else:
        status = "fail"

    ctx.add_result(
        test_id="charge_period_p1",
        name="Charge period 1 write (23:00–23:50) + entity read-back",
        status=status,
        write_ok=write_err is None,
        read_back_ok=read_ok,
        before=before_p1,
        attempted=test_p1.to_dict(),
        after=after_p1,
        error=write_err,
        notes=" ".join(notes),
    )

    restore_periods = [_period_to_config(before_p1), _period_to_config(before_p2)]

    async def _restore() -> None:
        try:
            await apply_charge_periods(
                ctx.hass,
                ctx.inverter_ref,
                restore_periods,
                entity_map=ctx.entity_map,
            )
            await _poll_charge_period_1(ctx, _period_to_config(before_p1))
        except Exception as err:
            _LOGGER.warning("Charge period restore failed: %s", err)

    ctx.restore.append(_RestoreAction("charge_periods", _restore))


async def _test_raw_write_48010(ctx: _ProbeContext) -> None:
    """Direct FC16 probe on 48010 (markybry PR block) — separate from entity path."""
    before_vals, read_err = await _read_holding(ctx.hass, ctx.inverter_ref, 48010, 1)
    before = before_vals.get(48010) if before_vals else None
    if read_err:
        ctx.add_result(
            test_id="raw_write_48010",
            name="Raw write holding 48010 + read-back",
            status="fail",
            before=before,
            error=f"Pre-read failed: {read_err}",
        )
        return

    probe_value = 0 if before != 0 else 1
    write_err: str | None = None
    try:
        await ctx.hass.services.async_call(
            MODBUS_DOMAIN,
            "write_registers",
            {
                "inverter": ctx.inverter_ref,
                "start_address": 48010,
                "values": str(probe_value),
            },
            blocking=True,
        )
    except Exception as err:
        write_err = str(err)

    read_ok = False
    after: int | None = None
    poll_s = 0.0
    poll_attempts = 0
    after_read_err: str | None = None
    notes = ["Low-level probe — IllegalAddress here means 480xx block is not writable on this path."]
    if write_err is None:
        read_ok, after, poll_s, poll_attempts, after_read_err = await _poll_holding_register(
            ctx.hass,
            ctx.inverter_ref,
            48010,
            probe_value,
        )
        notes.append(_timing_note(poll_s, poll_attempts))
    else:
        after, poll_s, after_read_err = await _settle_then_read_holding(ctx.hass, ctx.inverter_ref, 48010)
        poll_attempts = 1
        read_ok = after == probe_value and after_read_err is None
        notes.append(
            _timing_note(poll_s, poll_attempts, delayed=True)
            + " Write returned an error; re-read register after settle anyway."
        )
        if read_ok:
            notes.append("Register matched after settle despite write error — Modbus may be slow, not blocked.")

    ctx.add_result(
        test_id="raw_write_48010",
        name="Raw write holding 48010 + read-back",
        status="pass" if read_ok and write_err is None else ("warn" if read_ok else "fail"),
        write_ok=write_err is None,
        read_back_ok=read_ok,
        before=before,
        attempted=probe_value,
        after=after,
        error=write_err or after_read_err,
        notes=" ".join(notes),
    )

    if before is not None and (write_err is None or after != before):

        async def _restore() -> None:
            try:
                await ctx.hass.services.async_call(
                    MODBUS_DOMAIN,
                    "write_registers",
                    {
                        "inverter": ctx.inverter_ref,
                        "start_address": 48010,
                        "values": str(before),
                    },
                    blocking=True,
                )
                await _poll_holding_register(
                    ctx.hass,
                    ctx.inverter_ref,
                    48010,
                    before,
                )
            except Exception as err:
                _LOGGER.warning("48010 restore failed: %s", err)

        ctx.restore.append(_RestoreAction("raw_48010", _restore))


async def _test_max_charge_current(ctx: _ProbeContext) -> None:
    entity_id = _find_entity_by_suffix(ctx.hass, ctx.device_id, "max_charge_current")
    if not entity_id:
        ctx.add_result(
            test_id="max_charge_current",
            name="Max charge current write + read-back",
            status="skip",
            notes="max_charge_current entity not found on this inverter profile.",
        )
        return

    await ctx.hass.services.async_call(
        "homeassistant",
        "update_entity",
        {"entity_id": entity_id},
        blocking=True,
    )
    await asyncio.sleep(_PROBE_REFRESH_SLEEP_S)
    state = ctx.hass.states.get(entity_id)
    before_raw = state.state if state else None
    try:
        before = int(round(float(before_raw)))
    except (TypeError, ValueError):
        ctx.add_result(
            test_id="max_charge_current",
            name="Max charge current write + read-back",
            status="skip",
            before=before_raw,
            notes="Entity state not numeric.",
        )
        return

    target = before + 1 if before < 100 else before - 1
    if target == before:
        target = max(1, before - 1)

    write_err: str | None = None
    try:
        await ctx.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id, "value": float(target)},
            blocking=True,
        )
    except Exception as err:
        write_err = str(err)

    read_ok = False
    after: int | None = None
    poll_s = 0.0
    poll_attempts = 0
    if write_err is None:

        def _matches(raw: str | None) -> bool:
            try:
                return int(round(float(raw))) == target
            except (TypeError, ValueError):
                return False

        matched, after_raw, poll_s, poll_attempts = await async_poll_entity_id_live(
            ctx.hass,
            entity_id,
            expected=_matches,
            timeout_s=_WRITE_SETTLE_POLL_TIMEOUT_S,
            poll_interval_s=_POLL_INTERVAL_S,
        )
        read_ok = matched
        try:
            after = int(round(float(after_raw))) if after_raw is not None else None
        except (TypeError, ValueError):
            after = None

    ctx.add_result(
        test_id="max_charge_current",
        name="Max charge current write + read-back",
        status="pass" if write_err is None and read_ok else "fail",
        write_ok=write_err is None,
        read_back_ok=read_ok,
        before=before,
        attempted=target,
        after=after,
        error=write_err,
        notes=(
            _timing_note(poll_s, poll_attempts)
            if write_err is None
            else None
        ),
    )

    if write_err is None:

        async def _restore() -> None:
            await ctx.hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": entity_id, "value": float(before)},
                blocking=True,
            )

            def _matches_before(raw: str | None) -> bool:
                try:
                    return int(round(float(raw))) == before
                except (TypeError, ValueError):
                    return False

            await async_poll_entity_id_live(
                ctx.hass,
                entity_id,
                expected=_matches_before,
                timeout_s=_WRITE_SETTLE_POLL_TIMEOUT_S,
                poll_interval_s=_POLL_INTERVAL_S,
            )

        ctx.restore.append(_RestoreAction("max_charge_current", _restore))


async def run_modbus_debug_probe(coordinator: Any) -> dict[str, Any]:
    """Run the full probe battery; restores inverter state where possible."""
    plant = coordinator.plant
    ctx = _ProbeContext(
        hass=coordinator.hass,
        inverter_ref=plant.inverter_target or plant.device_id,
        entity_map=plant.entity_map,
        device_id=plant.device_id,
    )
    try:
        await _test_register_reads(ctx)
        await _test_entity_snapshot(ctx)
        await _test_work_mode(ctx)
        await _test_soc_limits(ctx)
        await _test_remote_control(ctx)
        await _test_charge_period(ctx)
        await _test_raw_write_48010(ctx)
        await _test_max_charge_current(ctx)
    finally:
        await _run_restore(ctx)
        await ctx.refresh_keys(
            (
                "work_mode",
                "remote_control",
                "min_soc",
                "min_soc_on_grid",
                "max_soc",
                *CHARGE_PERIOD_KEYS,
            )
        )

    passed = sum(1 for row in ctx.results if row["status"] == "pass")
    failed = sum(1 for row in ctx.results if row["status"] == "fail")
    skipped = sum(1 for row in ctx.results if row["status"] == "skip")
    warned = sum(1 for row in ctx.results if row["status"] == "warn")
    return {
        "summary": {
            "total": len(ctx.results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "warned": warned,
        },
        "tests": ctx.results,
        "inverter_ref": ctx.inverter_ref,
    }
