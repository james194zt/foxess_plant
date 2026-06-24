#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/charge_period.py \
  custom_components/foxess_plant/coordinator.py \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/remote_control.py \
  custom_components/foxess_plant/soc_limits.py \
  custom_components/foxess_plant/www/foxess-plant-panel.js \
  tools/_commit_v09373.sh
git commit -m "$(cat <<'EOF'
Fix EVO SOC writes and remote-control handling (v0.9.373).

Use atomic 46609-46611 block writes on EVO/H3 Pro, disable remote control
before SOC saves, and fix remote-control restore/discharge for EVO. Align
charge-period errors and work-mode UI with PR #1134 patterns.
EOF
)"
git push origin main
git status -sb
