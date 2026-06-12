#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

export GIT_AUTHOR_NAME=james194zt
export GIT_AUTHOR_EMAIL=james194zt@users.noreply.github.com
export GIT_COMMITTER_NAME=james194zt
export GIT_COMMITTER_EMAIL=james194zt@users.noreply.github.com

git add \
  custom_components/foxess_plant/discovery.py \
  custom_components/foxess_plant/__init__.py \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/manifest.json

git commit -m "Fix Impact after modbus reload by refreshing entity map (v0.9.235).

Re-discover foxess_modbus entities when lifetime yield is missing and drop
stale entity_id references; show a clearer Impact placeholder message."

git push origin main
