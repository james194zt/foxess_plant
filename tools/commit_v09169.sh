#!/bin/bash
set -euo pipefail
cd /mnt/c/Users/James/Documents/repo/foxess_plant
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/fox-device-icons.json \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  tools/extract_fox_device_icons.py
git -c user.name=James -c user.email=james194zt@users.noreply.github.com commit -m "$(cat <<'EOF'
Use Fox Cloud icon-d-battery1–4 for device summary cards (v0.9.169).

Replace wrong icon-phot/battery/discharge/minSoc assets with the 40×40 circle badges from the Fox device page.
EOF
)"
git push origin HEAD
git log -1 --oneline
git status --short
