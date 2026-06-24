#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/smart_charge/daily_plan.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  tools/_commit_v09371.sh
git commit -m "Build SmartCharge plan from current rates; clarify 16:00 refresh (v0.9.371)."
git push origin main
git status
