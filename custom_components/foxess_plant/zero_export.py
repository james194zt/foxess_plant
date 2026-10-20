"""Zero export: set the inverter's Export Power Limit to 0 W while the export price is negative.

The export limit only caps feed-in, so the inverter carries on in Self Use (solar still covers the house and
charges the battery). Remote Control at 0 W would pin the inverter's own output instead, so it isn't used.

Rules:
- Checked at every price boundary (and at startup, after a tariff save and after a settings save); never
  follows the house load. The fork limits the setting to one change a minute because the inverter probably
  keeps it in flash.
- Before writing 0, the limit it had is saved to .storage, so a restart in the middle of a negative slot still
  puts it back. Release writes back exactly that value, never anything higher.
- An unknown price, the setting being turned off, or Release Control all put the limit back.
- A failed write is retried every couple of minutes; after a few failures the user gets a notification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
ENTITY_SUFFIX = "_export_power_limit"
RETRY_SECONDS = 120
NOTIFY_AFTER_FAILURES = 3

ENGAGE = "engage"
RELEASE = "release"
HOLD = "hold"


@dataclass
class ZeroExportState:
    active: bool = False
    original_w: float | None = None
    since: str | None = None
    entity_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ZeroExportState:
        data = data or {}
        original = data.get("original_w")
        return cls(
            active=bool(data.get("active")),
            original_w=float(original) if original is not None else None,
            since=data.get("since"),
            entity_id=data.get("entity_id"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "original_w": self.original_w,
            "since": self.since,
            "entity_id": self.entity_id,
        }


def decide(*, enabled: bool, price_p: float | None, active: bool) -> str:
    """ENGAGE / RELEASE / HOLD. Only a known negative price keeps export at 0."""
    want = enabled and price_p is not None and price_p < 0
    if want and not active:
        return ENGAGE
    if not want and active:
        return RELEASE
    return HOLD


def find_export_limit_entity(hass: HomeAssistant, device_id: str | None) -> str | None:
    """The writable Export Power Limit number on the plant's inverter.

    Only ``number.*``: the read-only installer sensor (``…_installer_export_power_limit``) ends the same way.
    """
    if not device_id:
        return None
    reg = er.async_get(hass)
    for entry in er.async_entries_for_device(reg, device_id):
        if entry.domain == "number" and entry.entity_id.endswith(ENTITY_SUFFIX):
            return entry.entity_id
    return None


def _read_w(hass: HomeAssistant, entity_id: str) -> float | None:
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", ""):
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


class ZeroExportController:
    """Owns the saved state and the writes; the coordinator calls ``async_apply`` with the current price."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._store = Store(hass, STORAGE_VERSION, f"foxess_plant.zero_export.{entry_id}")
        self._entry_id = entry_id
        self.state = ZeroExportState()
        self._loaded = False
        self.failures = 0
        self.last_error: str | None = None
        self.last_price_p: float | None = None
        self.entity_id: str | None = None

    async def _async_load(self) -> None:
        if not self._loaded:
            self.state = ZeroExportState.from_dict(await self._store.async_load())
            self._loaded = True

    async def _async_save(self) -> None:
        # Saved straight away, not delayed: HA can stop at any moment and the original value must survive
        await self._store.async_save(self.state.to_dict())

    async def _async_set(self, entity_id: str, value_w: float) -> None:
        await self._hass.services.async_call(
            "number", "set_value", {"entity_id": entity_id, "value": value_w}, blocking=True
        )

    async def async_apply(
        self, *, enabled: bool, price_p: float | None, device_id: str | None
    ) -> bool:
        """Bring the limit in line with the price. Returns False if a write is still needed (retry later)."""
        await self._async_load()
        self.last_price_p = price_p
        action = decide(enabled=enabled, price_p=price_p, active=self.state.active)
        entity_id = self.state.entity_id if self.state.active else find_export_limit_entity(self._hass, device_id)
        self.entity_id = entity_id
        if action == HOLD:
            return True
        if entity_id is None:
            if action == ENGAGE:
                self.last_error = "This inverter has no writable Export Power Limit"
            return True
        try:
            if action == ENGAGE:
                current = _read_w(self._hass, entity_id)
                if current is None:
                    raise RuntimeError(f"{entity_id} isn't available")
                if current <= 0:
                    # Already not exporting (e.g. an installer zero-export setting): nothing to do or undo
                    return True
                self.state = ZeroExportState(
                    active=True, original_w=current, since=dt_util.utcnow().isoformat(), entity_id=entity_id
                )
                await self._async_save()
                await self._async_set(entity_id, 0)
                _LOGGER.info("Zero export on: export price %.2fp, %s was %.0f W", price_p, entity_id, current)
            else:
                original = self.state.original_w
                if original is not None and _read_w(self._hass, entity_id) != original:
                    await self._async_set(entity_id, original)
                _LOGGER.info("Zero export off: %s back to %s W", entity_id, original)
                self.state = ZeroExportState()
                await self._async_save()
        except Exception as err:  # noqa: BLE001 — retried; reported in the status and by notification
            self.failures += 1
            self.last_error = str(err)
            _LOGGER.warning("Zero export %s failed (%d): %s", action, self.failures, err)
            if self.failures == NOTIFY_AFTER_FAILURES:
                self._notify(action, err)
            return False
        self.failures = 0
        self.last_error = None
        self._dismiss()
        return True

    def _notify(self, action: str, err: Exception) -> None:
        from homeassistant.components import persistent_notification

        if action == RELEASE:
            message = (
                "Fox Plant couldn't put the inverter's Export Power Limit back to "
                f"{self.state.original_w:.0f} W after a negative export price ({err}). It keeps trying; "
                "until it succeeds the inverter won't export. You can also set it yourself on the inverter's "
                "Export Power Limit control."
            )
        else:
            message = f"Fox Plant couldn't set the Export Power Limit to 0 W for a negative export price ({err})."
        persistent_notification.async_create(
            self._hass, message, title="Fox Plant: Zero Export", notification_id=self._notification_id()
        )

    def _dismiss(self) -> None:
        from homeassistant.components import persistent_notification

        persistent_notification.async_dismiss(self._hass, self._notification_id())

    def _notification_id(self) -> str:
        return f"foxess_plant_zero_export_{self._entry_id}"

    def status(self, *, enabled: bool) -> dict[str, Any]:
        return {
            "enabled": enabled,
            "active": self.state.active,
            "original_w": self.state.original_w,
            "since": self.state.since,
            "entity_id": self.entity_id,
            "export_price_p": self.last_price_p,
            "last_error": self.last_error,
        }
