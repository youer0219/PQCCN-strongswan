#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ_FILE="$ROOT_DIR/requirements.txt"

python3 -m pip install --upgrade pip
python3 -m pip install -r "$REQ_FILE"

echo "Python dependencies installed."
