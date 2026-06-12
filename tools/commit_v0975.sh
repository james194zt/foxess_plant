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
v0.9.75: Add SOC line and dual Y-axis to statistics chart.

Overlay battery SoC on the day statistics chart with Fox-style Power (kW) left and SOC % right axes, plus SoC in the side legend and tooltip.
EOF

git push
git log -1 --oneline
