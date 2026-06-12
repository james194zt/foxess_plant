#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

export GIT_AUTHOR_NAME=james194zt
export GIT_AUTHOR_EMAIL=james194zt@users.noreply.github.com
export GIT_COMMITTER_NAME=james194zt
export GIT_COMMITTER_EMAIL=james194zt@users.noreply.github.com

git add \
  custom_components/foxess_plant/identity_format.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/manifest.json

git commit -m "Fix Version_BCU display when modbus returns formatted pack tokens (v0.9.234).

Merge pack 2 minor from formatted 0.004 when pack 1 is 1.000 (Fox 1.004)."

git push origin main
