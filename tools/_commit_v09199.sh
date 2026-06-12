#!/bin/bash
set -euo pipefail
cd /mnt/c/Users/James/Documents/repo/foxess_plant
git add custom_components/foxess_plant/manifest.json custom_components/foxess_plant/panel.py custom_components/foxess_plant/coordinator.py custom_components/foxess_plant/websocket_api.py
git commit -F tools/.commit_msg_v09199.txt
git push origin main
git status
