#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

author="$(git log -1 --format='%an')"
email="$(git log -1 --format='%ae')"
export GIT_AUTHOR_NAME="$author"
export GIT_AUTHOR_EMAIL="$email"
export GIT_COMMITTER_NAME="$author"
export GIT_COMMITTER_EMAIL="$email"

git add \
  custom_components/foxess_plant/const.py \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/models.py \
  custom_components/foxess_plant/panel_config.py \
  custom_components/foxess_plant/websocket_api.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/tariff_rates.py \
  custom_components/foxess_plant/tariff_store.py

git commit -F - <<'EOF'
v0.9.81: Add tariff settings and wire cost analysis on Analysis card.

Add Tariff settings for UK import/export rates and standing charge with manual entry or HA sensor sources, rate history storage, and Analysis summary rows for export revenue, import cost, and net daily cost with intraday sparklines.
EOF

git push
git log -1 --oneline
