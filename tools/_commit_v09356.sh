#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/www/weather \
  tools/_copy_weather_icons.sh \
  tools/_supplement_v1_from_v0.sh \
  tools/_compare_weather_icons.sh \
  tools/_commit_v09356.sh
git commit -m "Switch weather icons to Google v1 set and supplement missing conditions from v0 (v0.9.356)."
git push origin main
git status
