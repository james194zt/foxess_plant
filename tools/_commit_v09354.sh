#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/storm_weather.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/www/weather \
  tools/_copy_weather_icons.sh \
  tools/_commit_v09354.sh
git commit -m "Use Google Weather v2 light and dark icons for overview and hourly forecast (v0.9.354)."
git push origin main
git status
