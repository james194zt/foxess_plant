#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

author="$(git log -1 --format='%an')"
email="$(git log -1 --format='%ae')"
export GIT_AUTHOR_NAME="$author"
export GIT_AUTHOR_EMAIL="$email"
export GIT_COMMITTER_NAME="$author"
export GIT_COMMITTER_EMAIL="$email"

git add custom_components/foxess_plant/manifest.json custom_components/foxess_plant/www/foxess-plant-panel.js

git commit -F - <<'EOF'
v0.9.70: Add Analysis summary card and full-width statistics chart.

Stack supply and the new sparkline card above the chart in a 50/50 row; wire production and consumption trends while leaving revenue unwired.
EOF

git push
git log -1 --oneline
git status --short
