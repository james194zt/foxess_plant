#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/discovery.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/soc_limits.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  tools/_commit_v09376.sh
git commit -m "$(cat <<'EOF'
Improve EVO max SOC failure handling and pre-save prep (v0.9.376).

Clear remote-control work mode before SOC writes, skip unchanged limits,
detect EVO for register 46610 lockouts, and document Fox Mode Scheduler as
the usual cause when system max fails while mins succeed.
EOF
)"
git push origin main
git status -sb
