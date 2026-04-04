#!/bin/bash
# Configuration consolidation helper for configs/experiments.
# USAGE: bash configs/experiments/consolidate_configs.sh [--dry-run] [--archive]

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIGS_DIR="${ROOT_DIR}/configs/experiments/presets"
ARCHIVE_DIR="${ROOT_DIR}/configs/experiments/archived"
DRY_RUN=false
ARCHIVE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --archive) ARCHIVE=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

echo "=== Configuration Consolidation Plan ==="
echo "Dry Run: $DRY_RUN"
echo "Archive: $ARCHIVE"
echo ""

# Configs to KEEP (retained composite + quick set)
KEEP_CONFIGS=(
  "composite_ideal.yaml"
  "composite_metro.yaml"
  "composite_wan.yaml"
  "composite_lossy.yaml"
  "quick_classic_ideal.yaml"
  "quick_hybrid_ideal.yaml"
)

# Configs to REMOVE if they are still found in presets.
REMOVE_CONFIGS=(
  "dh.yaml"
  "delay_dh_baseline_win1.yaml"
  "delay_pq_win1.yaml"
  "burst_dh.yaml"
  "burst_pq.yaml"
  "delay_dh.yaml"
  "delay_pq.yaml"
  "duplicate.yaml"
  "duplicate_dh.yaml"
  "pkt_loss_dh.yaml"
  "pkt_loss_pq.yaml"
  "pkt_loss_extensive.yaml"
  "default.yaml"
)

echo "Configs to KEEP ($(echo ${#KEEP_CONFIGS[@]})):"
for cfg in "${KEEP_CONFIGS[@]}"; do
  if [ -f "$CONFIGS_DIR/$cfg" ]; then
    echo "  ✓ $cfg"
  else
    echo "  ✗ $cfg (not found)"
  fi
done
echo ""

echo "Configs to REMOVE ($(echo ${#REMOVE_CONFIGS[@]})):"
for cfg in "${REMOVE_CONFIGS[@]}"; do
  if [ -f "$CONFIGS_DIR/$cfg" ]; then
    echo "  - $cfg"
  fi
done
echo ""

if [ "$DRY_RUN" = true ]; then
  echo "[DRY RUN] Would remove the above configs. Run without --dry-run to execute."
  exit 0
fi

if [ "$ARCHIVE" = true ]; then
  mkdir -p "$ARCHIVE_DIR"
  echo "Archiving removed configs to $ARCHIVE_DIR..."
  for cfg in "${REMOVE_CONFIGS[@]}"; do
    if [ -f "$CONFIGS_DIR/$cfg" ]; then
      mv "$CONFIGS_DIR/$cfg" "$ARCHIVE_DIR/"
      echo "  Archived: $cfg"
    fi
  done
else
  echo "Removing redundant configs..."
  for cfg in "${REMOVE_CONFIGS[@]}"; do
    if [ -f "$CONFIGS_DIR/$cfg" ]; then
      rm "$CONFIGS_DIR/$cfg"
      echo "  Removed: $cfg"
    fi
  done
fi

echo ""
echo "=== Final Config List ==="
find "$CONFIGS_DIR" -maxdepth 1 -name "*.yaml" -printf "%f\n" | sort
echo ""
echo "Total configs: $(find "$CONFIGS_DIR" -maxdepth 1 -name '*.yaml' | wc -l)"
