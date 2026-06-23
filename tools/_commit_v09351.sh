#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/smart_charge_analysis.py \
  custom_components/foxess_plant/websocket_api.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  tests/test_smart_charge_analysis.py \
  tools/_commit_v09351.sh
git commit -m "Add SmartCharge Analysis report with planned vs actual grid import/export from recorder history (v0.9.351)."
git push origin main
git status
