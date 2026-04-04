#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
OUT_DIR="${1:-$ROOT_DIR/results/$(date +%Y%m%d_%H%M%S)}"

DEFAULT_CONFIGS=(
	"$ROOT_DIR/configs/experiments/presets/composite_ideal.yaml"
	"$ROOT_DIR/configs/experiments/presets/composite_metro.yaml"
	"$ROOT_DIR/configs/experiments/presets/composite_wan.yaml"
	"$ROOT_DIR/configs/experiments/presets/composite_lossy.yaml"
)

if [[ -n "${2:-}" ]]; then
	CFG_INPUT="$2"
else
	CFG_INPUT="$(IFS=','; echo "${DEFAULT_CONFIGS[*]}")"
fi

mkdir -p "$OUT_DIR"

cd "$ROOT_DIR"

echo "Running orchestration"
echo "  output: $OUT_DIR"
echo "  configs: $CFG_INPUT"

python3 -m pqccn_strongswan "$OUT_DIR" "$CFG_INPUT" --print-level 2 --collect-print-level 1

echo "Suite run complete."
