#!/usr/bin/env bash
# FoxESS Plant — WSL dev environment setup (run inside Ubuntu/WSL).
# Run from repo:  bash tools/wsl-setup.sh
# (If copied to /tmp, set FOXESS_PLANT_ROOT=/path/to/foxess_plant)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${FOXESS_PLANT_ROOT:-}" ]]; then
  REPO_ROOT="$(cd "${FOXESS_PLANT_ROOT}" && pwd)"
elif [[ -f "${SCRIPT_DIR}/../custom_components/foxess_plant/manifest.json" ]]; then
  REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
  for candidate in \
    "/mnt/c/Users/James/Documents/repo/foxess_plant" \
    "${HOME}/code/foxess_plant" \
    "${HOME}/foxess_plant"; do
    if [[ -f "${candidate}/custom_components/foxess_plant/manifest.json" ]]; then
      REPO_ROOT="$(cd "${candidate}" && pwd)"
      break
    fi
  done
  [[ -n "${REPO_ROOT:-}" ]] || {
    echo "Cannot find foxess_plant repo. cd to the clone and run: bash tools/wsl-setup.sh"
    exit 1
  }
fi
cd "$REPO_ROOT"

echo "==> FoxESS Plant WSL setup"
echo "    Repo: $REPO_ROOT"

# Windows-mounted repos (/mnt/c, /mnt/d, …) break venv ensurepip and npm chmod.
ON_WINDOWS_MOUNT=false
case "$REPO_ROOT" in
  /mnt/*) ON_WINDOWS_MOUNT=true ;;
esac

need_sudo=false
for pkg in python3-venv python3-pip gh; do
  if ! dpkg -s "$pkg" &>/dev/null; then
    need_sudo=true
    break
  fi
done

if $need_sudo; then
  echo "==> Installing system packages (sudo password may be required)..."
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git curl ca-certificates \
    python3 python3-venv python3-pip \
    gh
else
  echo "==> Core apt packages already installed"
fi

# Node via nvm (works on /mnt/c; apt nodejs is optional)
export NVM_DIR="${HOME}/.nvm"
if [[ ! -s "${NVM_DIR}/nvm.sh" ]]; then
  echo "==> Installing nvm..."
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
fi
# shellcheck source=/dev/null
set +u
. "${NVM_DIR}/nvm.sh"
nvm install --lts
nvm use --lts
set -u

if ! grep -q 'NVM_DIR' "${HOME}/.bashrc" 2>/dev/null; then
  cat >> "${HOME}/.bashrc" <<'EOF'

# Node (nvm) — FoxESS Plant frontend builds
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
EOF
  echo "==> Added nvm to ~/.bashrc"
fi

echo "==> Python venv for tools/ (Pillow, image scripts)"
VENV_DIR="${HOME}/.venvs/foxess_plant"
if $ON_WINDOWS_MOUNT; then
  echo "    (repo on /mnt/* — venv lives in ${VENV_DIR}, not tools/.venv)"
fi
python3 -m venv --without-pip "${VENV_DIR}" 2>/dev/null || true
if [[ ! -x "${VENV_DIR}/bin/pip" ]]; then
  curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip-foxess.py
  "${VENV_DIR}/bin/python" /tmp/get-pip-foxess.py -q
fi
"${VENV_DIR}/bin/pip" install --upgrade pip Pillow

echo "==> Frontend dependencies"
cd frontend
if $ON_WINDOWS_MOUNT; then
  npm config set bin-links false
fi
npm install
if $ON_WINDOWS_MOUNT; then
  node node_modules/vite/bin/vite.js build
else
  npm run build
fi
cd "$REPO_ROOT"
echo "    Built -> custom_components/foxess_plant/www/foxess-plant-panel.js"

echo ""
echo "==> Versions"
git --version
python3 --version
"${VENV_DIR}/bin/python" -c "import PIL; print('Pillow', PIL.__version__)"
node --version
npm --version
command -v gh >/dev/null && gh --version | head -1 || echo "gh: not installed (sudo apt install gh)"

echo ""
echo "==> Done"
echo "Activate Python tools venv:"
echo "  source ${VENV_DIR}/bin/activate"
echo ""
echo "Git identity (set once if commits fail):"
echo '  git config --global user.name "Your Name"'
echo '  git config --global user.email "you@example.com"'
echo ""
if $ON_WINDOWS_MOUNT; then
  echo "Tip: clone the repo under ~/code/foxess_plant for faster git/npm if you hit /mnt/c issues."
fi
