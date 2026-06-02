#!/usr/bin/env bash
# Decode Fox WEBP assets (misnamed .png) to real PNG sprites via dwebp.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WWW="$ROOT/custom_components/foxess_plant/www"

decode() {
  local src="$1" dst="$2"
  if [ ! -f "$src" ]; then
    echo "skip missing $src"
    return 0
  fi
  if head -c 4 "$src" | grep -q RIFF; then
    dwebp "$src" -o "$dst"
    echo "dwebp $(basename "$src") -> $(basename "$dst")"
  elif [ -f "$dst" ]; then
    echo "keep $(basename "$dst") (source already PNG)"
  else
    cp "$src" "$dst"
    echo "copy $(basename "$src") -> $(basename "$dst")"
  fi
}

for theme in day_light night_dark; do
  decode "$WWW/flow_pv_${theme}.png" "$WWW/flow_pv_${theme}_sprite.png"
  decode "$WWW/flow_aio_812_${theme}.png" "$WWW/flow_aio_812_${theme}_sprite.png"
done
