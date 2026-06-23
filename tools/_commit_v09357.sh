#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/www/octopus_greener_sapling.png \
  custom_components/foxess_plant/www/octopus_greener_sapling_green.png \
  tools/_commit_v09357.sh
git commit -m "Replace Octopus Greener Nights week-ahead saplings with custom PNG artwork (v0.9.357)."
git push origin main
git status
