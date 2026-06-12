#!/bin/bash
set -euo pipefail
cd /mnt/c/Users/James/Documents/repo/foxess_plant
git add custom_components/foxess_plant/manifest.json custom_components/foxess_plant/www/foxess-plant-panel.js tools/check_styles.py
git commit -F tools/.commit_msg_v09191.txt
git status
