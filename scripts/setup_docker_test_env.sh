#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$ROOT_DIR/pq-strongswan"
IMAGE_TAG="strongx509/pq-strongswan:latest"

cd "$ROOT_DIR"

echo "[1/5] Checking Docker availability..."
command -v docker >/dev/null 2>&1 || { echo "docker is not installed"; exit 1; }
docker version >/dev/null

echo "[2/5] Preparing certificate directory structure..."
if [[ -x "$COMPOSE_DIR/scripts/gen_dirs.sh" ]]; then
  (cd "$COMPOSE_DIR" && ./scripts/gen_dirs.sh)
fi

echo "[3/5] Ensuring image exists: $IMAGE_TAG"
if ! docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
  echo "Image not found locally, building from pq-strongswan/Dockerfile..."
  docker build -t "$IMAGE_TAG" "$COMPOSE_DIR"
fi

echo "[4/5] Starting compose services..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" up -d

echo "[5/5] Verifying containers..."
docker ps --filter "name=moon" --filter "name=carol"
echo "Docker test environment is ready."
