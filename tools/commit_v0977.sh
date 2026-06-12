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
v0.9.77: Stop Energy Analysis live updates restarting supply flow animation.

Patch top cards and summary values in place, stabilize chart slot updates, and use transform-based flow glow elements that survive layout reflows.
EOF

git push
git log -1 --oneline
