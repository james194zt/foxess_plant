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
  tools/_commit_v09369.sh
git rm -f custom_components/foxess_plant/www/fox-flow-scene-card-register.js 2>/dev/null || true
git add -u custom_components/foxess_plant/www/fox-flow-scene-card-register.js 2>/dev/null || true
git commit -m "Fix Fox Flow Scene picker spinner by bootstrapping custom element first (v0.9.369)."
git push origin main
git status
