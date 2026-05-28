#!/usr/bin/env bash
set -euo pipefail
VENV_DIR="${HOME}/.venvs/foxess_plant"
python3 -m venv --without-pip "${VENV_DIR}"
curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip-foxess.py
"${VENV_DIR}/bin/python" /tmp/get-pip-foxess.py -q
"${VENV_DIR}/bin/pip" install -q --upgrade pip Pillow
"${VENV_DIR}/bin/python" -c 'import PIL; print("Pillow", PIL.__version__)'
