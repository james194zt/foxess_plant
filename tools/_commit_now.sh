#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add custom_components/foxess_plant/manifest.json custom_components/foxess_plant/www/foxess-plant-panel.js tools/_commit_now.sh
git commit -m "Add spacing between Octopus greener card titles and headlines (v0.9.309).

Give the 24h forecast green headline and week-ahead card title bottom margin so the intro copy no longer sits flush underneath."
git push origin main
git status
