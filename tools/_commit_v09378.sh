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
  tools/_commit_v09378.sh
git commit -m "$(cat <<'EOF'
Suppress schedule drift banner during SmartCharge automation (v0.9.378).

Hide drift when an automation override is active so SmartCharge replanning
does not flash the banner, skip auto-reapply during automation modes, and
re-evaluate SmartCharge after syncing from the inverter.
EOF
)"
git push origin main
git status -sb
