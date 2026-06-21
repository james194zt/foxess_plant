#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
git add custom_components/foxess_plant/manifest.json custom_components/foxess_plant/www/foxess-plant-panel.js
git commit -m "$(cat <<'EOF'
Fix mobile panel layout for overview daily cards and device sidebar spacing.

Use container-query and narrow-mode stacking so daily production/consumption cards go full width in the HA app without breaking desktop side-by-side layout, and add row-gap between the device information card and summary cards on Analysis and Real-time.
EOF
)"
git push origin main
git status
