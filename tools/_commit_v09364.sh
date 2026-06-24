#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/__init__.py \
  custom_components/foxess_plant/lovelace_cards.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/fox-flow-scene-card.js \
  tools/_commit_v09364.sh
git commit -m "Add Fox Flow Scene Lovelace card with UI picker and auto resource registration (v0.9.364)."
git push origin main
git status
