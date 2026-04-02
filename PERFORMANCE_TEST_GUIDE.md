# PQCCN IPsec Performance Testing Guide

## Quick Start

### Exact Commands

**Lightweight test (5-10 minutes for quick validation):**
```bash
bash ./scripts/run_performance_test.sh quick
```

**Full test (3-4 hours, generates comprehensive report):**
```bash
bash ./scripts/run_performance_test.sh full
```

**Manual specification of output directory and configurations:**
```bash
# Test delay impact only
python3 Orchestration.py ./results/delay_only ./data_collection/configs/DataCollect_delay.yaml

# Test packet loss impact only
python3 Orchestration.py ./results/loss_only ./data_collection/configs/DataCollect_pktLoss.yaml

# Test combined fault scenarios
python3 Orchestration.py ./results/fault_matrix ./data_collection/configs/DataCollect_fault_injection_matrix.yaml
```

---

## Execution Time Estimation

### Time Calculation Formula
```
Single config duration ≈ [(3-5 sec/cycle × TC_Iterations) + 2 sec/log processing] × Steps + container startup/cleanup 30 sec
```

### Lightweight Test (QUICK) Time Breakdown

| Stage | Content | Duration | Notes |
|-------|---------|----------|-------|
| Docker startup/cleanup | Container initialization/cleanup | 1-2 min | Image pull typically fast (cached) |
| 1. Baseline | 3 IKE establishment cycles | 30 sec | No network faults, pure key exchange performance |
| 2. Delay | 3 delay values × 3 cycles | 1.5 min | Performance at 1/100/200ms delays |
| 3. Mixed Faults | 2 values (1% loss + 0.5% dup) × 3 cycles | 1 min | Performance under combined faults |
| Log processing/plotting | Statistics aggregation, plot generation | 1-2 min | PlotAudit.csv, PNG, ExperimentReport.md output |
| **Total** | | **5-10 min** | |

### Full Test (FULL) Time Breakdown

| Config | Steps | Iter | Base Time | Actual Time | Notes |
|--------|-------|------|-----------|-------------|-------|
| baseline | 1 | 10 | 50 sec | 45-60 sec | Diffie-Helman vs Post-Quantum |
| delay | 5 | 10 | 8 min | 8-12 min | 1-200ms, incremental sweep |
| loss | 5 | 10 | 8 min | 8-12 min | 0.1%-25% packet loss rate sweep |
| rate | 21 | 10 | 35 min | 40-50 min | 128-4 kbps bandwidth limiting |
| fault_matrix | 8 | 12 | 20 min | 20-30 min | Multiple fault combinations (delay+loss+reorder+corrupt) |
| Docker/log processing | — | — | — | 10-15 min | Container lifecycle, statistics aggregation, plotting |
| **Total** | | | **~70 min** | **3-4 hours** | |

> **Note**: Actual duration depends on:
> - Cryptographic algorithm complexity (Post-Quantum typically 30-50% slower than DH)
> - Docker image first-time pull (if uncached, add 5-10 min)
> - Log file size (more complex configs generate larger logs)

---

## Test Coverage Scenarios

### Ideal Environment (Baseline)
- **Purpose**: Establish performance baseline
- **Conditions**: No network delay, no packet loss, unlimited bandwidth
- **Metrics**: IKE establishment time (ms), CPU utilization, memory peak
- **Command**:
  ```bash
  python3 Orchestration.py ./results/baseline ./data_collection/configs/DataCollect_baseline.yaml
  ```

### Single Parameter Sweep Scenarios

#### Delay Impact (1-200ms)
```bash
python3 Orchestration.py ./results/delay_sweep ./data_collection/configs/DataCollect_delay.yaml
```
- **Key Metrics**: Impact of delay on IKE handshake, connection success rate

#### Packet Loss Impact (0.1%-25%)
```bash
python3 Orchestration.py ./results/loss_sweep ./data_collection/configs/DataCollect_pktLoss.yaml
```
- **Key Metrics**: Packet loss tolerance, retransmission frequency

#### Bandwidth Constraint Impact (128-4 kbps)
```bash
python3 Orchestration.py ./results/rate_sweep ./data_collection/configs/DataCollect_rate_PQ.yaml
```
- **Key Metrics**: Tunnel establishment and throughput at extreme low speeds

### Combined Fault Scenario
```bash
python3 Orchestration.py ./results/fault_matrix ./data_collection/configs/DataCollect_fault_injection_matrix.yaml
```
- **Fault Combinations**: Delay + packet loss + reordering + corruption (realistic network model)
- **Key Metrics**: Stability, fault recovery capability

---

## Result Output Example

After completion, result directory structure is as follows:
```
results/
├── perf_quick_20260401_0240/
│   ├── ExperimentReport.md              ← One-page experiment summary
│   ├── PlotAudit.csv                    ← Plot quality checklist
│   ├── RunLogStatsDF.csv                ← Complete statistics data
│   ├── RunLogStatsDF_summary.csv        ← Quick reference table
│   ├── 20260401_0240_baseline_vs_mean.png
│   ├── 20260401_0240_delay_vs_ConnectionPercent.png
│   └── ...
└── perf_full_20260401_0500/
    └── (More plots and complete data)
```

### ExperimentReport.md Content Example
```markdown
# Experiment Report

Generated: 2026-04-01T02:40:01
Result Directory: results/perf_quick_20260401_0240

## Dataset Overview
- Total rows: 150
- Algorithms: Diffie-Helman, Post-Quantum
- VariParams: baseline, delay, loss, fault_matrix

## Key Metrics
| Algorithm | VariParam | mean (ms) | ConnectionPercent | IterationTime (s) |
| --- | --- | ---: | ---: | ---: |
| Diffie-Helman | baseline | 0.034 | 99.5% | 3.2 |
| Post-Quantum | baseline | 0.051 | 98.8% | 4.8 |
| ... | ... | ... | ... | ... |

## Plot Audit
| VariParam | Stat | Points | XRange | YRange | Note | Image |
| --- | --- | ---: | --- | --- | --- | --- |
| delay | mean | 50 | [1, 200] | [0.03, 0.20] | ok | 20260401_delay_vs_mean.png |
| loss | ConnectionPercent | 50 | [0.1%, 25%] | [90, 100] | ok | 20260401_loss_vs_connpct.png |
```

---

## Recommended Testing Strategy

### Development/Validation Phase
```bash
# 1. Quick check if framework works correctly
bash ./scripts/run_performance_test.sh quick

# 2. If successful, perform deep sweep on critical scenarios
python3 Orchestration.py ./results/delay_detailed \
  ./data_collection/configs/DataCollect_delay.yaml

# 3. View detailed comparison report
cat results/delay_detailed/ExperimentReport.md
```

### Final Result Generation
```bash
# Full test (run overnight or over weekends)
nohup bash ./scripts/run_performance_test.sh full > perf_test.log 2>&1 &

# Monitor progress
tail -f perf_test.log
```

---

## Key Metrics Interpretation

| Metric | Meaning | Target/Expected |
|--------|---------|-----------------|
| **IKE Setup Time (mean)** | Average IKE handshake time | PQ should be 20-40% slower than DH |
| **ConnectionPercent** | Percentage of successful connection establishment | > 95% considered healthy |
| **IterationTime** | Total time per cycle | Should increase with delay/loss |
| **Jitter (std)** | Performance variability | Low jitter indicates good stability |

---

## Troubleshooting

**Issue**: Docker container fails to start
```bash
# Rebuild image
docker build -t strongx509/pq-strongswan:latest ./pq-strongswan

# Manually test startup
bash ./scripts/setup_docker_test_env.sh
```

**Issue**: Test hangs (no progress for >10 minutes)
```bash
# Check container status
docker ps

# View collection logs
tail -f results/*/runstats.txt
```

**Issue**: Plot or report generation fails
```bash
# Check dependencies
python3 -c "import plotnine, pandas; print('OK')"

# Re-run data processing
python3 - <<'EOF'
from data_parsing import ProcessLogs
from reporting import generate_experiment_report
df = ProcessLogs.Log_stats('./results/latest', 2)
generate_experiment_report('./results/latest', df, None)
EOF
```

---

## Crypto Matrix: 3 Security Modes + Parameterized Network Profiles

Use the new matrix runner to execute all of the following in one run:

1. Classic-KEX + Classic-Cert
2. PurePQ-KEX + PQ-Cert
3. Hybrid-KEX (Classic+PQ) + PQ-Cert

The pure-PQ mode uses `pq-strongswan/pq-only-docker-compose.yml`.
The hybrid-KEX mode uses `pq-strongswan/docker-compose.yml` (classic + post-quantum KEX in the same proposal).

### One-command Matrix Run

```bash
python3 scripts/run_crypto_matrix.py \
  --result-dir ./results/crypto_matrix_$(date +%Y%m%d_%H%M) \
  --profiles rtt,loss,rate,mixed \
  --rtt-ms 0,20,50,100 \
  --loss-pct 0,0.1,0.5,1,2 \
  --rate-kbit 4000,2000,1000,512 \
  --jitter-ms 2 \
  --iterations 8
```

Single-line equivalent (safer when copy/pasting in some terminals):

```bash
python3 scripts/run_crypto_matrix.py --result-dir ./results/crypto_matrix_$(date +%Y%m%d_%H%M) --profiles rtt,loss,rate,mixed --rtt-ms 0,20,50,100 --loss-pct 0,0.1,0.5,1,2 --rate-kbit 4000,2000,1000,512 --jitter-ms 2 --iterations 8
```

Preview only (generate configs and print execution plan without running):

```bash
python3 scripts/run_crypto_matrix.py --profiles rtt --rtt-ms 0,50 --iterations 2 --dry-run --show-configs
```

### Parameter Notes

- `--rtt-ms`: RTT values (ms). Internally converted to one-way delay for `tc netem`.
- `--loss-pct`: loss sweep points for loss profile.
- `--rate-kbit`: bandwidth sweep points for rate profile.
- `--profiles`: choose from `rtt,loss,rate,mixed` (any subset).
- `--static-loss-pct`, `--static-rate-kbit`: fixed companion faults used by non-loss/non-rate profiles.

### P50/P95/P99 Outputs

The pipeline now computes and reports latency percentiles:

- `p50`, `p95`, `p99` in `RunLogStatsDF.csv`
- percentile plots (alongside mean/median/success-rate/iteration-time)
- one combined percentile figure per VariParam (`*_percentile_summary.png`) showing P50/P95/P99 together
- grouped percentile tables in `ExperimentReport.md`
