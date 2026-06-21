#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add -A
git commit -m "Rename 24h greener forecast card and highlight week-ahead intro (v0.9.301).

Retitle the carbon forecast card to Octopus Green Nights 24h Forecast and style the week-ahead Greener Nights window text with the same green headline treatment."
git push origin main
git status
