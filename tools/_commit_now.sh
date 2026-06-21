#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add -A
git commit -m "Improve Octopus Greener Nights charts and add weekly Energy Analysis views (v0.9.298).

Plot carbon bars by low-carbon score, fix the Y-axis arrow, add weekly greener-nights charts for Energy Analysis week mode, and add an Octopus-style upcoming week card beneath the forecast card."
git status
