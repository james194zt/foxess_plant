#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/soc_limits.py \
  tools/_commit_v09375.sh
git commit -m "$(cat <<'EOF'
Fix EVO SOC writes with sequential FC6 registers (v0.9.375).

EVO rejects FC16 multi-register writes at 46609 (IllegalAddress). Write
off-grid min, system min, then max as single number entities instead.
EOF
)"
git push origin main
git status -sb
