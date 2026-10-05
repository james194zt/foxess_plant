#!/usr/bin/env bash
# Syntax-check the Fox Plant panel bundle and run the chart smoke test.
# Usage (WSL / Linux, Node 18+):  bash tools/check_panel_js.sh
set -euo pipefail

cd "$(dirname "$0")/.."
WWW=custom_components/foxess_plant/www

# node --check only treats .mjs as an ES module, so check copies under that extension.
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
for f in foxess-plant-panel.js fox-alarm-guide.js fox-flow-scene-card.js; do
  cp "$WWW/$f" "$tmp/${f%.js}.mjs"
  node --check "$tmp/${f%.js}.mjs"
  echo "syntax OK  $WWW/$f"
done

node tools/test_panel_charts.mjs
node tools/test_warmup_tariff.mjs
node tools/test_alarm_sources.mjs
