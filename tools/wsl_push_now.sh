#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="James"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="James"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
/usr/bin/git commit --amend \
  -m "Add Solcast next-fetch status and overview Battery SOC chart (v0.9.29)." \
  -m "Show estimated next PV poll time in Solcast settings. Add a midnight-to-midnight SOC chart under Statistics with 0/50/100% scale and charge/discharge coloring."
/usr/bin/git log -1 --oneline
/usr/bin/git push origin main
