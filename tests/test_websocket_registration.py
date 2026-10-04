"""Registering the websocket API evaluates every command decorator.

Catches handlers whose schema refers to a removed WS_TYPE constant (a NameError that only shows up when
Home Assistant loads the integration).
"""

from unittest.mock import patch

from custom_components.foxess_plant import websocket_api as ws


class _FakeHass:
    def __init__(self) -> None:
        self.data: dict = {}


def test_all_websocket_commands_register() -> None:
    registered = []
    with patch.object(ws.websocket_api, "async_register_command", lambda _hass, handler: registered.append(handler)):
        ws.async_register_ws_handlers(_FakeHass())

    assert registered, "no websocket commands registered"
    types = [handler._ws_command for handler in registered]
    assert all(types), "a handler is missing its websocket command type"
    assert len(types) == len(set(types)), "duplicate websocket command types"
