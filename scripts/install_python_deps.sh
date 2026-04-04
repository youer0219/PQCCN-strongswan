#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"

cd "$ROOT_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[1/4] Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
else
  echo "[1/4] Reusing virtual environment at $VENV_DIR"
fi

echo "[2/4] Upgrading pip, setuptools, and wheel"
"$VENV_PY" -m pip install --upgrade pip setuptools wheel

echo "[3/4] Installing project and dev dependencies"
"$VENV_PY" -m pip install -e ".[dev]"

echo "[4/4] Environment ready"
echo "Next steps:"
echo "  . \"$VENV_DIR/bin/activate\""
echo "  python -m pytest -q"
echo "  bash ./scripts/setup_docker_test_env.sh"
echo "  bash ./scripts/run_performance_test.sh quick"
