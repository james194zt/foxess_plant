#!/usr/bin/env bash
set -eu
cd /mnt/c/Users/James/Documents/repo/foxess_plant
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/solcast_forecast_chart.py \
  custom_components/foxess_plant/storm_weather.py \
  custom_components/foxess_plant/solcast_forecast_accuracy.py \
  custom_components/foxess_plant/websocket_api.py
export GIT_AUTHOR_NAME="James"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="James"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git commit -F tools/_commit_now_msg.txt
git push -u origin HEAD
git log -1 --oneline
