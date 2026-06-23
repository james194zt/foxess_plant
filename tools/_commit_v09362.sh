#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/bg_smart_charge.png \
  custom_components/foxess_plant/www/bg_storm_safe_charging.png \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  tools/_convert_hero_pngs.py \
  tools/_commit_v09362.sh
git commit -m "Fix SmartCharge and StormSafe hero banners as real PNG assets (v0.9.362)."
git push origin main
git status
