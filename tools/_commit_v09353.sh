#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add \
  custom_components/foxess_plant/manifest.json \
  custom_components/foxess_plant/octopus_graphql.py \
  custom_components/foxess_plant/octopus_greener.py \
  tests/test_octopus_rewards.py \
  tools/_commit_v09353.sh
git commit -m "Fix Octopoints display with layered GraphQL fallbacks for loyalty balance and ledger queries (v0.9.353)."
git push origin main
git status
