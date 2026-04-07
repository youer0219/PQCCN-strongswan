#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
OUT_DIR="${1:-$ROOT_DIR/results/$(date +%Y%m%d_%H%M%S)}"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"

if [[ -x "${VENV_PYTHON}" ]]; then
	PYTHON_BIN="${VENV_PYTHON}"
elif command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="$(command -v python3)"
else
	echo "python3 not found. Run: bash ./scripts/install_python_deps.sh" >&2
	exit 1
fi

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
echo "  python: $PYTHON_BIN"

"$PYTHON_BIN" -m pqccn_strongswan "$OUT_DIR" "$CFG_INPUT" --print-level 2 --collect-print-level 1

echo "Suite run complete."
