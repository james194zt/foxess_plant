#!/bin/bash
set -e
cd /mnt/c/Users/James/Documents/repo/foxess_plant
git add \
  custom_components/foxess_plant/const.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/foxess-plant-panel.js
git commit -F tools/_commit_health_v09167_msg.txt
git push origin HEAD
