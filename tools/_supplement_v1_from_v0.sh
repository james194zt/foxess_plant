#!/bin/bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLONE="${TMPDIR:-/tmp}/gwi-compare"
if [[ ! -d "$CLONE/icons/weather/v0/light" ]]; then
  rm -rf "$CLONE"
  git clone --depth 1 --filter=blob:none --sparse https://gitlab.com/bignutty/google-weather-icons.git "$CLONE"
  cd "$CLONE"
  git sparse-checkout set icons/weather/v0/light icons/weather/v0/dark icons/weather/v1/light icons/weather/v1/dark
fi
DEST="$REPO_ROOT/custom_components/foxess_plant/www/weather/v1"
mkdir -p "$DEST/light" "$DEST/dark"
added=0
for theme in light dark; do
  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    if [[ ! -f "$DEST/$theme/$name" ]]; then
      cp "$CLONE/icons/weather/v0/$theme/$name" "$DEST/$theme/$name"
      added=$((added + 1))
    fi
  done < <(comm -23 <(ls "$CLONE/icons/weather/v0/$theme" | sort) <(ls "$CLONE/icons/weather/v1/$theme" | sort))
done
echo "Supplemented v1 bundle with $added v0-only icon files"
