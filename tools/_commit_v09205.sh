#!/bin/bash
set -e
cd /mnt/c/Users/James/Documents/repo/foxess_plant
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/solcast_forecast_chart.py \
  custom_components/foxess_plant/websocket_api.py \
  custom_components/foxess_plant/solcast_forecast_accuracy.py
git commit -F tools/.commit_msg_v09205.txt
git status
git push
