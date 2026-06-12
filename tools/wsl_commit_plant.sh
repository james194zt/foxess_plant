#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/James/Documents/repo/foxess_plant
/usr/bin/git -c user.name=James -c user.email=james194zt@users.noreply.github.com \
  commit -F tools/commit_msg_v0944.txt
/usr/bin/git log -1 --oneline
/usr/bin/git push origin main
