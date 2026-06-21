#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add -A
git commit -m "Use Octopus plant icons and align greener card headers with Statistics (v0.9.300).

Replace upcoming-week seedling art with official Octopus SVGs, switch the week-ahead card to standard card styling, and match both greener card titles to the Statistics header treatment."
git push origin main
git status
