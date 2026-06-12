#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="James"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="James"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"

if git diff --quiet && git diff --cached --quiet; then
  # Fix mangled HEAD commit message (no file changes).
  git commit --amend \
    -m "Show persisted Solcast forecast on statistics chart after restart (v0.9.27)." \
    -m "Use cached detailed_forecast without waiting for hobbyist re-bind, invalidate the chart when forecast content changes, and refresh plant state before load."
  git push --force-with-lease origin main
else
  git add custom_components/foxess_plant/manifest.json custom_components/foxess_plant/www/foxess-plant-panel.js
  git commit -F tools/.git_commit_msg.txt
  git push origin main
fi

git log -1 --oneline
git status -sb
