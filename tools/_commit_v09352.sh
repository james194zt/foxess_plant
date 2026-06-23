#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/const.py \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/discovery.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/smart_charge/battery_metrics.py \
  custom_components/foxess_plant/smart_charge/grid_charge.py \
  custom_components/foxess_plant/smart_charge/solcast_budget.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  tests/test_smart_charge_battery_metrics.py \
  tools/_commit_v09352.sh
git commit -m "Fix SmartCharge battery SOC and capacity resolution for EVO BMS entities and sibling modbus devices (v0.9.352)."
git push origin main
git status
