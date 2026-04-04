#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m pip install --upgrade pip
python3 -m pip install -e "$ROOT_DIR"

echo "Python package and dependencies installed in editable mode."
