#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_AUTHOR_NAME="james194zt"
export GIT_AUTHOR_EMAIL="james194zt@users.noreply.github.com"
export GIT_COMMITTER_NAME="james194zt"
export GIT_COMMITTER_EMAIL="james194zt@users.noreply.github.com"
git add custom_components/foxess_plant/manifest.json custom_components/foxess_plant/octopus_api.py custom_components/foxess_plant/octopus_tariff.py tools/_commit_now.sh
git commit -m "Fix Octopus product lookup for regional Flexible and variable tariffs (v0.9.312).

Derive product codes from standard E-1R tariff names and walk nested GSP tariff structures when searching the products API."
git push origin main
git status
