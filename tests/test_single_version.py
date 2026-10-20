"""The release version lives only in manifest.json (the panel reads it from the file name HA serves it under)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "custom_components" / "foxess_plant"


def test_version_is_only_in_the_manifest() -> None:
    version = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))["version"]
    panel = (PKG / "www" / "foxess-plant-panel.js").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f'"{version}"' not in panel, "panel JS hard-codes the version; it reads it from its served file name"
    assert "Current release" not in readme and version not in readme, "README repeats the version"
