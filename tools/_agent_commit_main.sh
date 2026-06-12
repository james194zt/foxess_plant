#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/James/Documents/repo/foxess_plant
GIT=/usr/bin/git
TREE=cc0686b4b85ae23360648522997d17a47f5e8991
PARENT=3b16b667ac7af6dc2b0209e8041f1bbf884f0431
cat > /tmp/foxess_commit_msg.txt <<'MSGEOF'
Restore cached Solcast forecast after restart (v0.9.31).

Fix empty prior commit; sync panel JS version with manifest.
MSGEOF
INDEX=$($GIT write-tree)
echo "index_tree=$INDEX"
if [ "$INDEX" != "$TREE" ]; then
  $GIT add custom_components/foxess_plant/coordinator.py custom_components/foxess_plant/manifest.json custom_components/foxess_plant/websocket_api.py custom_components/foxess_plant/www/foxess-plant-panel.js
fi
NEW_SHA=$($GIT commit-tree "$TREE" -p "$PARENT" -F /tmp/foxess_commit_msg.txt)
echo "NEW_SHA=$NEW_SHA"
if [ -z "$NEW_SHA" ]; then echo EMPTY_SHA_ABORT; exit 1; fi
$GIT update-ref refs/heads/main "$NEW_SHA"
$GIT reset --hard "$NEW_SHA"
echo "--- log -1 --stat ---"
$GIT log -1 --stat
echo "--- manifest grep ---"
grep 0.9.31 custom_components/foxess_plant/manifest.json
echo "--- push ---"
$GIT push origin main