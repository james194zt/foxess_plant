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
  custom_components/foxess_plant/sensor.py \
  custom_components/foxess_plant/binary_sensor.py \
  custom_components/foxess_plant/manifest.json

git commit -m "Fix Plant sensors going unavailable after entity map refresh (v0.9.237).

Stop dropping entity mappings when modbus states are temporarily unavailable;
harden discovery with fallbacks; keep mode/binary sensors available; defer
config entry writes until after coordinator refresh completes."

git push origin main
