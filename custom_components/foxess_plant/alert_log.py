"""Fox Plant's own log of inverter alerts, kept in .storage so the Alerts page can show more than HA's history.

Sources (all from the linked foxess_modbus device):
- the Inverter Alarms sensor ("None" or "Alarm A; Alarm B")
- the six BMS1 Fault raw sensors (37626-37631); the bits aren't named by Fox, so they're "Battery fault N bit B"
- the Modbus Connection Status sensor ("Connected" or not)

The log keeps raised / cleared events. A reading of unknown / unavailable is a gap, not a clear.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
MAX_EVENTS = 1000
INVERTER_NOT_RESPONDING = "Inverter not responding (Modbus)"
NO_READING = frozenset({"unknown", "unavailable", "", None})

SOURCE_ALARMS = "alarms"
SOURCE_CONNECTION = "connection"


def bms_source(index: int) -> str:
    return f"bms_{index}"


def alert_names(source: str, state: Any) -> set[str] | None:
    """Alert names a sensor state represents, or None when there's no reading."""
    if state in NO_READING:
        return None
    text = str(state)
    if source == SOURCE_ALARMS:
        return {part.strip() for part in text.split(";") if part.strip() and part.strip() != "None"}
    if source == SOURCE_CONNECTION:
        return set() if text == "Connected" else {INVERTER_NOT_RESPONDING}
    if source.startswith("bms_"):
        try:
            value = int(float(text))
        except ValueError:
            return None
        register = source.split("_", 1)[1]
        return {
            f"Battery fault {register} bit {bit} (0x{1 << bit:04x})" for bit in range(16) if value & (1 << bit)
        }
    return None


def diff_events(previous: set[str], current: set[str], when: str, source: str) -> list[dict[str, Any]]:
    """Raised / cleared events between two sets of active alert names."""
    return [{"t": when, "action": "raised", "name": name, "source": source} for name in sorted(current - previous)] + [
        {"t": when, "action": "cleared", "name": name, "source": source} for name in sorted(previous - current)
    ]


def open_alerts(events: list[dict[str, Any]]) -> dict[str, str]:
    """Alert name -> source for every alert raised but not cleared yet."""
    open_: dict[str, str] = {}
    for event in events:
        if event.get("action") == "raised":
            open_[event["name"]] = event.get("source", "")
        else:
            open_.pop(event.get("name"), None)
    return open_


class AlertLogStore:
    """Bounded JSON list of alert events in .storage."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"foxess_plant.alert_log.{entry_id}")
        self.events: list[dict[str, Any]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load()
        events = data.get("events") if isinstance(data, dict) else None
        self.events = [e for e in events or [] if isinstance(e, dict) and e.get("name")]

    def add(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        self.events.extend(events)
        if len(self.events) > MAX_EVENTS:
            self.events = self.events[-MAX_EVENTS:]
        self._store.async_delay_save(lambda: {"events": self.events}, 5)
        for event in events:
            _LOGGER.info("Inverter alert %s: %s", event["action"], event["name"])
