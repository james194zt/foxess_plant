#!/bin/bash
set -e
cd /mnt/c/Users/James/Documents/repo/foxess_plant

TREE=cc0686b4b85ae23360648522997d17a47f5e8991
PARENT=$(/usr/bin/git rev-parse HEAD)

cat > /tmp/fpcmsg.txt <<'EOF'
Restore cached Solcast forecast after restart (v0.9.31).

Fix empty prior commit; sync panel JS version with manifest.
EOF

NEW=$(/usr/bin/git commit-tree "$TREE" -p "$PARENT" -F /tmp/fpcmsg.txt)
echo "NEW=$NEW"
/usr/bin/git update-ref refs/heads/main "$NEW"
/usr/bin/git reset --hard "$NEW"
/usr/bin/git log -1 --stat
/usr/bin/git push origin main
