"""The served panel pins its imported modules to their content, so a browser can't pair it with an old copy."""

import re

from custom_components.foxess_plant import panel


def test_served_panel_imports_the_alarm_guide_by_content_hash() -> None:
    served = panel._versioned_panel_bytes().decode()
    imports = re.findall(r'^import .* from "(\./fox-alarm-guide\.js[^"]*)";', served, re.MULTILINE)
    assert imports == [f"./fox-alarm-guide.js?v={panel._module_hash('fox-alarm-guide.js')}"]


def test_panel_fingerprint_follows_the_imported_module(monkeypatch) -> None:
    before = panel._panel_js_fingerprint()
    monkeypatch.setattr(panel, "_module_hash", lambda name: "changed00000")
    assert panel._panel_js_fingerprint() != before
