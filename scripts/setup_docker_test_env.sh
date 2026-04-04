#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$ROOT_DIR/pq-strongswan"
COMPOSE_FILE="$COMPOSE_DIR/hybrid2pq-docker-compose.yml"
IMAGE_TAG="strongx509/pq-strongswan:latest"

cd "$ROOT_DIR"

echo "[1/6] Checking Docker availability..."
command -v docker >/dev/null 2>&1 || { echo "docker is not installed"; exit 1; }
docker version >/dev/null
docker compose version >/dev/null

echo "[2/6] Preparing certificate directory structure..."
sh "$COMPOSE_DIR/scripts/gen_dirs.sh"

echo "[3/6] Pulling image when available: $IMAGE_TAG"
if ! docker pull "$IMAGE_TAG"; then
  echo "Image pull failed; will fall back to local build if needed."
fi

echo "[4/6] Ensuring image exists locally..."
if ! docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
  echo "Image not available locally, building from pq-strongswan/Dockerfile..."
  docker build -t "$IMAGE_TAG" "$COMPOSE_DIR"
fi

echo "[5/6] Starting compose services..."
docker compose -f "$COMPOSE_FILE" up -d

echo "[6/6] Verifying containers..."
running_services="$(docker compose -f "$COMPOSE_FILE" ps --status running --services)"
printf '%s\n' "$running_services"

grep -qx "moon" <<<"$running_services" || { echo "moon service is not running"; exit 1; }
grep -qx "carol" <<<"$running_services" || { echo "carol service is not running"; exit 1; }
grep -qx "lanhost" <<<"$running_services" || { echo "lanhost service is not running"; exit 1; }

echo "Docker test environment is ready."
