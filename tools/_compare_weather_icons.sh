#!/bin/bash
set -euo pipefail
CLONE=/tmp/gwi-compare
rm -rf "$CLONE"
git clone --depth 1 --filter=blob:none --sparse https://gitlab.com/bignutty/google-weather-icons.git "$CLONE"
cd "$CLONE"
git sparse-checkout set icons/weather/v0/light icons/weather/v0/dark icons/weather/v1/light icons/weather/v1/dark
echo "=== v0 only (light) ==="
comm -23 <(ls icons/weather/v0/light | sort) <(ls icons/weather/v1/light | sort)
echo "=== v1 only (light) ==="
comm -13 <(ls icons/weather/v0/light | sort) <(ls icons/weather/v1/light | sort)
echo "=== v0 only (dark) ==="
comm -23 <(ls icons/weather/v0/dark | sort) <(ls icons/weather/v1/dark | sort)
