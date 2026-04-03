#!/bin/bash
# Configuration Consolidation Script
# This script helps consolidate redundant test configurations and reorganize them.
# USAGE: bash consolidate_configs.sh [--dry-run] [--archive]

set -e

CONFIGS_DIR="./data_collection/configs"
ARCHIVE_DIR="${CONFIGS_DIR}/archived_configs"
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
  "DataCollect_composite_ideal.yaml"
  "DataCollect_composite_metro.yaml"
  "DataCollect_composite_wan.yaml"
  "DataCollect_composite_harsh.yaml"
  "DataCollect_quick_classic_ideal.yaml"
  "DataCollect_quick_hybrid_ideal.yaml"
)

# Configs to REMOVE (duplicates, outdated, or specific-algorithm variants)
REMOVE_CONFIGS=(
  "DataCollect_DH.yaml"
  "DataCollect_Delay_DH_baseline_WIN1.yaml"
  "DataCollect_Delay_PQ_WIN1.yaml"
  "DataCollect_burst_DH.yaml"
  "DataCollect_burst_PQ.yaml"
  "DataCollect_delay_DH.yaml"
  "DataCollect_delay_PQ.yaml"
  "DataCollect_duplicate.yaml"
  "DataCollect_duplicate_DH.yaml"
  "DataCollect_pktLoss_DH.yaml"
  "DataCollect_pktLoss_PQ.yaml"
  "DataCollect_pktLoss_extensive.yaml"
  "DataCollect.yaml"
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
ls -1 "$CONFIGS_DIR"/DataCollect_*.yaml | xargs -n1 basename | sort
echo ""
echo "Total configs: $(ls -1 "$CONFIGS_DIR"/DataCollect_*.yaml 2>/dev/null | wc -l)"
