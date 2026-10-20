"""The served panel pins its imported modules to their content, so a browser can't pair it with an old copy."""

import re

from custom_components.foxess_plant import panel


def test_served_panel_imports_the_alarm_guide_by_content_hash() -> None:
    served = panel._versioned_panel_bytes().decode()
    imports = re.findall(r'^import .* from "(\./fox-alarm-guide\.js[^"]*)";', served, re.MULTILINE)
    assert imports == [f"./fox-alarm-guide.js?v={panel._module_hash('fox-alarm-guide.js')}"]


def test_element_tag_changes_with_every_build_and_matches_the_panel_js() -> None:
    # The panel JS works its tag out from the module URL (panelElementTag); HA is told the same name
    url = panel._panel_js_module_url()
    m = re.search(r"foxess-plant-panel\.v(\d+)_(\d+)_(\d+)\.([a-f0-9]+)\.js", url)
    assert m
    assert panel._panel_component_name() == f"foxess-plant-panel-{m[1]}_{m[2]}_{m[3]}-{m[4]}"
    assert m[4] == panel._panel_js_fingerprint()


def test_panel_fingerprint_follows_the_labels(monkeypatch, tmp_path) -> None:
    before = panel._panel_js_fingerprint()
    labels = tmp_path / "i18n"
    labels.mkdir()
    (labels / "en.json").write_text('{"panel.overview": "Overview!"}', encoding="utf-8")
    monkeypatch.setattr(panel, "I18N_DIR", labels)
    assert panel._panel_js_fingerprint() != before


def test_panel_fingerprint_follows_the_imported_module(monkeypatch) -> None:
    before = panel._panel_js_fingerprint()
    monkeypatch.setattr(panel, "_module_hash", lambda name: "changed00000")
    assert panel._panel_js_fingerprint() != before


def test_plant_state_before_registration_reads_nothing_from_disk(monkeypatch) -> None:
    # The real startup warning: the coordinator's first refresh asked for the panel info before the panel was
    # registered, and the fallback hashed the JS in the event loop (seen on HA 2026.9.4 with 0.9.532)
    class FakeHass:
        data = {}

    def no_disk(*_args, **_kwargs):
        raise AssertionError("disk read in the event loop")

    monkeypatch.setattr(panel.Path, "read_bytes", no_disk)
    monkeypatch.setattr(panel.Path, "open", no_disk)
    monkeypatch.setattr(panel.Path, "glob", no_disk)
    assert panel.get_panel_disk_info(FakeHass()) == {}


def test_panel_config_reads_nothing_from_disk_in_the_event_loop(monkeypatch) -> None:
    # HA flagged "blocking call to read_bytes" x8 at startup: the config re-read the panel JS for its fingerprint
    class FakeHass:
        data = {}

    hass = FakeHass()
    hass.data[panel._PANEL_DISK_INFO_KEY] = panel._compute_panel_disk_info()  # done in the executor for real

    def no_disk(*_args, **_kwargs):
        raise AssertionError("disk read in the event loop")

    monkeypatch.setattr(panel.Path, "read_bytes", no_disk)
    monkeypatch.setattr(panel.Path, "open", no_disk)
    config = panel._build_frontend_panel_config(hass)
    assert config["_panel_custom"]["module_url"] == hass.data[panel._PANEL_DISK_INFO_KEY]["module_url"]
    assert config["_panel_custom"]["name"] == hass.data[panel._PANEL_DISK_INFO_KEY]["element"]
