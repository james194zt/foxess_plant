#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add -A
git commit -m "Add Octopus Energy Analysis report with polled smart-meter history (v0.9.311).

Introduce Reports sub-tab with price/carbon charts, greener compliance, and forecast history; poll Octopus consumption every 30 minutes into persistent storage and recorder-friendly sensors."
git push origin main
git status
