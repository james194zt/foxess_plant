#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

author="$(git log -1 --format='%an')"
email="$(git log -1 --format='%ae')"
export GIT_AUTHOR_NAME="$author"
export GIT_AUTHOR_EMAIL="$email"
export GIT_COMMITTER_NAME="$author"
export GIT_COMMITTER_EMAIL="$email"

git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  custom_components/foxess_plant/www/fox-analysis-icons.json \
  tools/extract_fox_analysis_icons.py

git commit -F - <<'EOF'
v0.9.72: Match Fox supply/usage card icons, borders, and flow animation.

Extract Fox Cloud SVG icons from the public app bundle and replicate the gradient border rows plus CSS gradient flow lines from plants-analysis CSS.
EOF

git push
git log -1 --oneline
