#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="James"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="James"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/identity_format.py
git commit -F tools/.commit_msg_v09232.txt
git push origin main
git log -1 --oneline
