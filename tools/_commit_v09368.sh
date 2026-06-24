#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/lovelace_cards.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/fox-flow-scene-card.js \
  custom_components/foxess_plant/www/fox-flow-scene-card-register.js \
  tools/_commit_v09368.sh
git commit -m "Fix Fox Flow Scene card picker infinite spinner (define before register) (v0.9.368)."
git push origin main
git status
