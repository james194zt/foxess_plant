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
  tests/test_soc_model_detection.py \
  tools/_commit_v09374.sh
git commit -m "$(cat <<'EOF'
Fix EVO max SOC detection for atomic 46609-46611 writes (v0.9.374).

Match foxess_modbus full model strings (e.g. EVO 10-5.0-H) when choosing the
contiguous SOC block path, resolve via linked number entities, and retry with an
atomic block if a single 46610 write still fails.
EOF
)"
git push origin main
git status -sb
