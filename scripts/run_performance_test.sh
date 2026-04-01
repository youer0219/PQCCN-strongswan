#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cat <<'EOF'
====================================================================
PQCCN IKEv2 Post-Quantum Performance Test Suite
====================================================================

This suite measures the performance impact of post-quantum key exchange 
(e.g., Kyber-3, BIKE-3) on IPsec tunnel establishment and throughput 
under various network conditions.

Two test modes available:

  QUICK (5-10 min):  Ideal + Simple Delay + Mixed Faults (fast validation)
  FULL  (3-4 hours): Comprehensive Ideal/Delay/Loss/Rate/Fault scenarios

====================================================================
EOF

case "${1:-}" in
  quick)
    echo ""
    echo "Starting QUICK test suite (5-10 minutes expected)..."
    echo ""
    start=$(date +%s)
    bash ./scripts/setup_docker_test_env.sh >/dev/null 2>&1 || true
    sleep 2
    python3 Orchestration.py "./results/perf_quick_$(date +%Y%m%d_%H%M)" \
      "./data_collection/configs/DataCollect_baseline_quick.yaml,./data_collection/configs/DataCollect_delay_quick.yaml,./data_collection/configs/DataCollect_fault_quick.yaml" \
      --print-level 1 --collect-print-level 1
    end=$(date +%s)
    elapsed=$((end - start))
    echo ""
    echo "QUICK test completed in $(printf '%02d:%02d:%02d\n' $((elapsed/3600)) $((elapsed%3600/60)) $((elapsed%60)))"
    echo ""
    ;;
  full)
    echo ""
    echo "Starting FULL test suite (3-4 hours expected)..."
    echo ""
    start=$(date +%s)
    bash ./scripts/setup_docker_test_env.sh >/dev/null 2>&1 || true
    sleep 2
    python3 Orchestration.py "./results/perf_full_$(date +%Y%m%d_%H%M)" \
      "./data_collection/configs/DataCollect*.yaml" \
      --print-level 2 --collect-print-level 1
    end=$(date +%s)
    elapsed=$((end - start))
    echo ""
    echo "FULL test completed in $(printf '%02d:%02d:%02d\n' $((elapsed/3600)) $((elapsed%3600/60)) $((elapsed%60)))"
    echo ""
    ;;
  *)
    cat <<'USAGE'

Usage: bash run_performance_test.sh [MODE]

Modes:
  quick     Quick validation (5-10 min): baseline + simple delay + mixed faults
  full      Full suite (3-4 hours): all delay/loss/rate/fault scenarios
  
Examples:
  bash run_performance_test.sh quick
  bash run_performance_test.sh full

Timing Breakdown:
  
  QUICK (~7 min):
    - baseline: 30s (3 IKE cycles, ~3s each)
    - delay: 1m30s (3 values × 3 cycles)
    - mixed faults: 1m (2 values × 3 cycles)
    - Docker startup/teardown: 2m
    - Log processing/plotting: 1-2m
  
  FULL (~3.5 hours):
    - baseline: 50s (10 IKE cycles, ~5s each - varies based on crypto)
    - delay sweep: 8m (5 values × 10+ cycles)
    - loss sweep: 8m (5 values × 10+ cycles)  
    - rate limiting: 15m (21 values × 10+ cycles)
    - combined faults: 20m (8 values × 12 cycles)
    - Docker startup/teardown: 5m
    - Log processing/plotting/report: 10-15m

Outputs:
  results/
    └─ perf_*/
       ├─ ExperimentReport.md        (one-page summary)
       ├─ PlotAudit.csv              (plot quality metrics)
       ├─ RunLogStatsDF.csv           (full statistics)
       ├─ RunLogStatsDF_summary.csv   (compact view)
       └─ *.png                       (scatter plots with trend lines)

Requirements:
  - Docker daemon running
  - Python 3.8+ with numpy/pandas/plotnine (see requirements.txt)
  - 5-20 GB free disk space (for logs and images)
  - Network access to strongX509/pq-strongswan image

Notes:
  - Each test compares Post-Quantum (Kyber-3/BIKE-3) vs. Diffie-Hellman
  - Metrics: connection %, setup time, throughput, jitter
  - See ExperimentReport.md for detailed results and plot index
USAGE
    ;;
esac
