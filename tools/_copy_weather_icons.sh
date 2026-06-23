#!/bin/bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLONE_DIR="${TMPDIR:-/tmp}/google-weather-icons"
if [[ ! -d "$CLONE_DIR/icons/weather/v1/light" ]]; then
  rm -rf "$CLONE_DIR"
  git clone --depth 1 --filter=blob:none --sparse https://gitlab.com/bignutty/google-weather-icons.git "$CLONE_DIR"
  cd "$CLONE_DIR"
  git sparse-checkout set icons/weather/v1/light icons/weather/v1/dark
fi
SRC="$CLONE_DIR/icons/weather/v1"
DEST="$REPO_ROOT/custom_components/foxess_plant/www/weather/v1"
mkdir -p "$DEST"
cp -r "$SRC/light" "$DEST/"
cp -r "$SRC/dark" "$DEST/"
echo "Copied $(ls "$DEST/light" | wc -l) light and $(ls "$DEST/dark" | wc -l) dark v1 icons"
bash "$(dirname "$0")/_supplement_v1_from_v0.sh"
