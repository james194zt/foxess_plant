#!/bin/bash
set -euo pipefail
SRC=/tmp/google-weather-icons/icons/weather/v2
DEST="$(dirname "$0")/../custom_components/foxess_plant/www/weather/v2"
mkdir -p "$DEST"
cp -r "$SRC/light" "$DEST/"
cp -r "$SRC/dark" "$DEST/"
echo "Copied $(ls "$DEST/light" | wc -l) light and $(ls "$DEST/dark" | wc -l) dark icons"
