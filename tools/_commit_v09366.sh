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
  tools/_commit_v09366.sh
git commit -m "Always register Fox Flow Scene card via frontend module URL for YAML dashboards (v0.9.366)."
git push origin main
git status
