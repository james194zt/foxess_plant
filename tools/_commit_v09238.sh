#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

export GIT_AUTHOR_NAME=james194zt
export GIT_AUTHOR_EMAIL=james194zt@users.noreply.github.com
export GIT_COMMITTER_NAME=james194zt
export GIT_COMMITTER_EMAIL=james194zt@users.noreply.github.com

git add -A
git commit -m "Revert BCU/AFCI work and restore stable entity discovery (v0.9.238).

Remove identity_format, entity-map refresh hacks, and BCU/AFCI panel rows.
Restore simple foxess_modbus discovery so device info and sensors work again."

git push origin main
