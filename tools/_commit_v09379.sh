#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/smart_charge/daily_plan.py \
  custom_components/foxess_plant/smart_charge/spread.py \
  custom_components/foxess_plant/smart_charge/strategy.py \
  custom_components/foxess_plant/smart_charge_analysis.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  tools/_commit_v09379.sh
git commit -m "$(cat <<'EOF'
Fix misleading SmartCharge status and rename solar gap fill (v0.9.379).

Stop forcing grid charge when the energy budget says skip, show Armed only
when windows are applied, rename winter fill to solar gap fill, and fix
degenerate plan slot time labels.
EOF
)"
git push origin main
git status -sb
