#!/bin/bash
set -euo pipefail
cd /mnt/c/Users/James/Documents/repo/foxess_plant
export GIT_AUTHOR_NAME='James'
export GIT_AUTHOR_EMAIL='james194zt@users.noreply.github.com'
git add custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/solcast_forecast_chart.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js
git commit -F tools/.commit_msg_v09200.txt
git push origin main
git status
