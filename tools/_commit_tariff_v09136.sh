#!/usr/bin/env bash
set -eu
cd /mnt/c/Users/James/Documents/repo/foxess_plant
git add \
  custom_components/foxess_plant/__init__.py \
  custom_components/foxess_plant/const.py \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/models.py \
  custom_components/foxess_plant/sensor.py \
  custom_components/foxess_plant/tariff_rates.py \
  custom_components/foxess_plant/tariff_schedule.py \
  custom_components/foxess_plant/websocket_api.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js
export GIT_AUTHOR_NAME="James"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="James"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git commit -F tools/_commit_now_msg.txt
git push -u origin HEAD
git log -1 --oneline
git status --short
