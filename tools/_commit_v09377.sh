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
  tools/_commit_v09377.sh
git commit -m "$(cat <<'EOF'
Fix schedule drift detection and sync clearing (v0.9.377).

Normalize charge-period times when comparing desired vs inverter state,
refresh period entities before sync/re-apply, and align override periods
when syncing from the inverter so the drift banner clears correctly.
EOF
)"
git push origin main
git status -sb
