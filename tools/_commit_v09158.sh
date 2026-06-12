#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/solcast_forecast_accuracy.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js
git commit -m "$(cat <<'EOF'
Fix forecast accuracy graph disappearing when navigating to other days (v0.9.158).

Use recorder-first loading for past days, cancel stale in-flight fetches on date change, and stop hiding the card when data is empty.
EOF
)"
git push origin main
git status
