#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

export GIT_AUTHOR_NAME=james194zt
export GIT_AUTHOR_EMAIL=james194zt@users.noreply.github.com
export GIT_COMMITTER_NAME=james194zt
export GIT_COMMITTER_EMAIL=james194zt@users.noreply.github.com

git add \
  custom_components/foxess_plant/discovery.py \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/const.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/manifest.json

git commit -m "Fix Impact yield discovery when modbus entities are orphaned (v0.9.236).

Find Yield Total by foxess_modbus unique_id and EVO friendly name, not only
device_id linkage; panel fallback reads yield sensor directly from HA states."

git push origin main
