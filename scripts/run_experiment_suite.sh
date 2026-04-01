#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$ROOT_DIR/results/$(date +%Y%m%d_%H%M%S)}"
CFG_INPUT="${2:-$ROOT_DIR/data_collection/configs/*.yaml}"

mkdir -p "$OUT_DIR"

cd "$ROOT_DIR"

echo "Running orchestration"
echo "  output: $OUT_DIR"
echo "  configs: $CFG_INPUT"

python3 Orchestration.py "$OUT_DIR" "$CFG_INPUT" --print-level 2 --collect-print-level 1

echo "Suite run complete."
