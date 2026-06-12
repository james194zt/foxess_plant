#!/usr/bin/env bash
cd /mnt/c/Users/James/Documents/repo/foxess_plant
git add custom_components/foxess_plant/manifest.json custom_components/foxess_plant/solcast_forecast_chart.py custom_components/foxess_plant/www/foxess-plant-panel.js
git commit -F tools/_commit_v09144_msg.txt
git status --short
git push
