#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add -A
git commit -m "Polish Octopus 24h forecast copy, legend, and timeline styling (v0.9.305).

Add the daily carbon intro and NESO help bubble, move the chart legend above the graph with a dashed national line marker, restyle greener-night tiles and Energy Analysis headers, and rebuild the advice timeline with Octopus leaf and unplugged icons on a side rail."
git push origin main
git status
