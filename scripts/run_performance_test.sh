#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DEFAULT_COMPOSITE_CASES="ideal:0:0:0;metro:12:2:0.1;wan:68:12:0.6;lossy:135:22:2.0"

QUICK_CONFIGS=(
  "${ROOT_DIR}/data_collection/configs/DataCollect_quick_classic_ideal.yaml"
  "${ROOT_DIR}/data_collection/configs/DataCollect_quick_hybrid_ideal.yaml"
)

join_by_comma() {
  local IFS=','
  echo "$*"
}

format_hms() {
  local total="$1"
  printf '%02d:%02d:%02d\n' $((total/3600)) $((total%3600/60)) $((total%60))
}

ensure_images() {
  local result_dir="$1"
  local p50_svg="${result_dir}/matrix_algo_scenario_p50.svg"
  local p95_svg="${result_dir}/matrix_algo_scenario_p95.svg"
  local p99_svg="${result_dir}/matrix_algo_scenario_p99.svg"

  if [[ -f "${p50_svg}" && -f "${p95_svg}" && -f "${p99_svg}" ]]; then
    echo "[Images] Matrix percentile SVGs already generated."
    return 0
  fi

  if [[ ! -f "${result_dir}/RunLogStatsDF.csv" ]]; then
    echo "[Images] RunLogStatsDF.csv not found; skip image regeneration."
    return 1
  fi

  echo "[Images] Regenerating SVG outputs from RunLogStatsDF.csv ..."
  python3 - <<PY
from pathlib import Path
import pandas as pd
from summarize_matrix_results import generate_matrix_svgs
from summarize_results import generate_packet_bytes_from_dataframe

out_dir = Path(${result_dir@Q})
df = pd.read_csv(out_dir / "RunLogStatsDF.csv")
generate_matrix_svgs(df, out_dir)
generate_packet_bytes_from_dataframe(df, out_dir)
PY

  if [[ -f "${p50_svg}" && -f "${p95_svg}" && -f "${p99_svg}" ]]; then
    echo "[Images] Matrix percentile SVGs generated successfully."
    return 0
  fi

  echo "[Images] Warning: matrix percentile SVGs are still missing."
  return 1
}

run_quick() {
  local result_dir="${ROOT_DIR}/results/perf_quick_$(date +%Y%m%d_%H%M)"
  local print_level=1
  local collect_level=1
  local dry_run=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --result-dir)
        result_dir="$2"
        shift 2
        ;;
      --print-level)
        print_level="$2"
        shift 2
        ;;
      --collect-print-level)
        collect_level="$2"
        shift 2
        ;;
      --dry-run)
        dry_run=1
        shift
        ;;
      *)
        echo "Unknown option for quick mode: $1"
        return 1
        ;;
    esac
  done

  local config_list
  config_list="$(join_by_comma "${QUICK_CONFIGS[@]}")"

  echo "[Quick] Result dir: ${result_dir}"
  echo "[Quick] Configs   : ${config_list}"

  if [[ "${dry_run}" -eq 1 ]]; then
    echo "[Quick] Dry-run enabled; no experiment executed."
    return 0
  fi

  local start end elapsed
  start=$(date +%s)
  bash "${ROOT_DIR}/scripts/setup_docker_test_env.sh" >/dev/null 2>&1 || true
  python3 "${ROOT_DIR}/Orchestration.py" "${result_dir}" "${config_list}" \
    --print-level "${print_level}" --collect-print-level "${collect_level}"
  end=$(date +%s)
  elapsed=$((end - start))

  ensure_images "${result_dir}" || true
  echo "[Quick] Completed in $(format_hms "${elapsed}")"
  echo "[Quick] Report: ${result_dir}/ExperimentReport.md"
}

run_large() {
  local result_dir="./results/perf_large_$(date +%Y%m%d_%H%M)"
  local composite_cases="${DEFAULT_COMPOSITE_CASES}"
  local iterations=200
  local warmup_iters=20
  local max_time_s=7200
  local print_level=1
  local collect_level=1
  local dry_run=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --result-dir)
        result_dir="$2"
        shift 2
        ;;
      --composite-cases)
        composite_cases="$2"
        shift 2
        ;;
      --iterations)
        iterations="$2"
        shift 2
        ;;
      --warmup-iters)
        warmup_iters="$2"
        shift 2
        ;;
      --max-time-s)
        max_time_s="$2"
        shift 2
        ;;
      --print-level)
        print_level="$2"
        shift 2
        ;;
      --collect-print-level)
        collect_level="$2"
        shift 2
        ;;
      --dry-run)
        dry_run=1
        shift
        ;;
      *)
        echo "Unknown option for large mode: $1"
        return 1
        ;;
    esac
  done

  local cmd=(
    python3 "${ROOT_DIR}/scripts/run_crypto_matrix.py"
    --result-dir "${result_dir}"
    --composite-cases "${composite_cases}"
    --iterations "${iterations}"
    --warmup-iters "${warmup_iters}"
    --max-time-s "${max_time_s}"
    --print-level "${print_level}"
    --collect-print-level "${collect_level}"
  )

  if [[ "${dry_run}" -eq 1 ]]; then
    cmd+=(--dry-run --show-configs)
  fi

  echo "[Large] Composite cases: ${composite_cases}"
  echo "[Large] Iterations     : ${iterations}"

  local start end elapsed
  start=$(date +%s)
  bash "${ROOT_DIR}/scripts/setup_docker_test_env.sh" >/dev/null 2>&1 || true
  "${cmd[@]}"
  end=$(date +%s)
  elapsed=$((end - start))

  if [[ "${dry_run}" -eq 0 ]]; then
    local abs_result_dir
    if [[ "${result_dir}" = /* ]]; then
      abs_result_dir="${result_dir}"
    else
      abs_result_dir="${ROOT_DIR}/${result_dir#./}"
    fi
    ensure_images "${abs_result_dir}" || true
    echo "[Large] Report: ${abs_result_dir}/ExperimentReport.md"
  fi

  echo "[Large] Completed in $(format_hms "${elapsed}")"
}

print_usage() {
  cat <<'USAGE'
Usage:
  bash scripts/run_performance_test.sh quick [options]
  bash scripts/run_performance_test.sh large [options]

Modes:
  quick   Fast validation using a small classic+hybrid config set.
  large   Unified large-scale test via one parameterized matrix script.

quick options:
  --result-dir <dir>
  --print-level <n>
  --collect-print-level <n>
  --dry-run

large options:
  --result-dir <dir>
  --composite-cases "ideal:0:0:0;metro:12:2:0.1;wan:68:12:0.6;lossy:135:22:2.0[:rate_kbit]"
  --iterations <n>
  --warmup-iters <n>
  --max-time-s <sec>
  --print-level <n>
  --collect-print-level <n>
  --dry-run

Notes:
  - Composite case format is name:rtt_ms:jitter_ms:loss_pct[:rate_kbit]
  - RTT is automatically converted to one-way delay for netem
  - Omitted rate_kbit means unlimited bandwidth (internally -1)
  - Script checks/repairs SVG generation after non-dry-run execution
USAGE
}

mode="${1:-}"
if [[ -z "${mode}" ]]; then
  print_usage
  exit 1
fi
shift || true

case "${mode}" in
  quick)
    run_quick "$@"
    ;;
  large)
    run_large "$@"
    ;;
  *)
    print_usage
    exit 1
    ;;
esac
