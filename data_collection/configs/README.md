# Test Configuration Files

This directory contains YAML configuration files for the IPsec performance testing framework.

## Core Configurations (Recommended)

### Quick Test Suite (5-10 minutes total)
Use these for rapid validation and development iteration:

| Config | Purpose | Steps | Iterations | Duration |
|--------|---------|-------|-----------|----------|
| `DataCollect_baseline_quick.yaml` | Baseline performance (ideal network) | 1 | 3 | ~30 sec |
| `DataCollect_delay_quick.yaml` | Delay impact (1/100/200ms) | 3 | 3 | ~1.5 min |
| `DataCollect_fault_quick.yaml` | Mixed faults (1% loss + 0.5% dup) | 2 | 3 | ~1 min |
| **Total** | | | | **5-10 min** |

### Full Test Suite (3-4 hours total)
Use these for comprehensive performance analysis:

| Config | Scenario | Steps | Iterations | Range | Duration |
|--------|----------|-------|-----------|-------|----------|
| `DataCollect_baseline.yaml` | Baseline performance | 1 | 10 | — | ~1 min |
| `DataCollect_delay.yaml` | Delay sweep | 5 | 10 | 1-200ms | ~8-12 min |
| `DataCollect_pktLoss.yaml` | Packet loss sweep | 5 | 10 | 0.1%-25% | ~8-12 min |
| `DataCollect_rate_PQ.yaml` | Bandwidth limiting | 21 | 10 | 128-4000 kbps | ~40-50 min |
| `DataCollect_fault_injection_matrix.yaml` | Multi-fault combinations | 8 | 12 | Multiple | ~20-30 min |
| **Total** | | | | | **3-4 hours** |

### Template
- `DataCollect_TEMPLATE.yaml` - Commented template for creating new configurations

---

## Usage

### Quick Validation (5-10 min)
```bash
bash ./scripts/run_performance_test.sh quick
```
Equivalent to running baseline_quick, delay_quick, and fault_quick sequentially.

### Full Test Suite (3-4 hours)
```bash
bash ./scripts/run_performance_test.sh full
```
Equivalent to running all core configs in sequence.

### Individual Config Test
```bash
python3 Orchestration.py ./results/my_test ./data_collection/configs/DataCollect_delay.yaml
```

### Multiple Configs
```bash
# Directory: all .yaml files
python3 Orchestration.py ./results/batch ./data_collection/configs/

# Wildcard: specific matching pattern
python3 Orchestration.py ./results/quick "./data_collection/configs/*quick.yaml"

# Comma-list: explicit selection
python3 Orchestration.py ./results/custom "baseline_quick.yaml,delay_quick.yaml"
```

---

## File Organization

```
configs/
├── DataCollect_*.yaml           # Active core configurations
├── DataCollect_TEMPLATE.yaml    # Template for new configs
├── CONFIG_REFERENCE.md          # Detailed configuration documentation
├── README.md                    # This file
├── archived_configs/            # Previous/redundant configurations (preserved for reference)
│   ├── DataCollect_DH.yaml
│   ├── DataCollect_burst_DH.yaml
│   ├── DataCollect_delay_DH.yaml
│   └── ... (12 archived files)
└── consolidate_configs.sh       # Consolidation utility script
```

---

## Configuration Parameters Reference

### CoreConfig

| Parameter | Type | Example | Note |
|-----------|------|---------|------|
| `TC_Iterations` | int | 3-10 | Cycles per constraint value (quick: 3, production: 10+) |
| `MaxTimeS` | int | 36000 | Max run duration (seconds) |
| `LocalPath` | string | "../../" | Local log storage directory |
| `RemotePath` | string | "/var/log/charon.log" | Container log file path |
| `CommandRetries` | int | 2 | Retry failed commands |
| `TrafficCommand` | string | "ping -c 2 10.1.0.2" | Optional background traffic |
| `PrintLevel` | int | 0-3 | Verbosity (0=silent, 3=debug) |
| `compose_files` | string | "./pq-strongswan/docker-compose.yml" | Docker Compose file |
| `Note` | string | "delay-sweep" | Metadata for results tracking |

### Constraint Configuration

| Parameter | Type | Example | Units | Note |
|-----------|------|---------|-------|------|
| `Constraint` | string | "delay", "loss", "rate" | — | What to sweep |
| `Interface` | string | "eth0" | — | Target network interface |
| `StartRange` | number | 1 | varies | Minimum sweep value |
| `EndRange` | number | 200 | varies | Maximum sweep value |
| `Units` | string | "ms", "%", "kbps" | — | Unit of measurement |
| `Steps` | int | 5 | — | Number of sweep points |
| `AddParams` | string | "" | — | Extra tc/netem parameters |

---

## Creating New Configurations

1. Copy `DataCollect_TEMPLATE.yaml` to `DataCollect_YOURNAME.yaml`
2. Edit `CoreConfig` for your test parameters
3. Define or modify constraint sections
4. Test: `python3 Orchestration.py ./results/test <config_file>`

Example: Testing extreme latency on asymmetric paths
```yaml
---
CoreConfig:
  TC_Iterations: 5
  MaxTimeS: 3600
  LocalPath: "../../results/extreme_latency/"
  Note: "Extreme latency test (500-2000ms asymmetric)"

Carol_TC_Config:
  Constraint1:
    Type: netem
    Constraint: delay
    Interface: eth0
    StartRange: 500
    EndRange: 2000
    Units: ms
    Steps: 4
    AddParams: 'distribution normal'
```

---

## Archived Configurations

Previous algorithm-specific configurations have been archived to `archived_configs/`:

- `DataCollect_DH.yaml` - Baseline (DH-only)
- `DataCollect_delay_DH.yaml` - Delay test (DH-only)
- `DataCollect_delay_PQ.yaml` - Delay test (PQ-only)
- `DataCollect_pktLoss_DH.yaml`, `_PQ.yaml` - Loss tests per algo
- `DataCollect_burst_DH.yaml`, `_PQ.yaml` - Burst traffic tests
- `DataCollect_duplicate_DH.yaml` - Packet duplication
- `DataCollect_pktLoss_extensive.yaml` - Extended loss sweep
- `DataCollect_Delay_DH_baseline_WIN1.yaml`, `_PQ_WIN1.yaml` - Windows-specific tests
- `DataCollect.yaml` - Legacy generic config

Why weren't these removed entirely?
- **Preserve history** in case specific algorithm tests need re-running
- **Prevent accidental loss** of experimental configurations
- **Audit trail** for comparing against old results

To restore an archived config:
```bash
mv archived_configs/DataCollect_<name>.yaml ./
```

---

## Performance Estimation

Quick calculation for config duration:
```
Duration ≈ (TC_Iterations × Steps × 3-4 sec/cycle) + 30 sec overhead
```

Examples:
- baseline: `1 × 1 × 3 + 30 = 33 sec`
- delay_quick: `3 × 3 × 3 + 30 = 57 sec`
- delay_full: `10 × 5 × 4 + 30 = 230 sec (~4 min)`

Note: Post-Quantum algorithms typically add 20-50% to execution time.

---

## Recommended Test Workflows

### Development Phase
```bash
# 1. Validate framework with quick suite
bash ./scripts/run_performance_test.sh quick

# 2. Deep dive on critical path (e.g., delay)
python3 Orchestration.py ./results/delay_detail ./data_collection/configs/DataCollect_delay.yaml

# 3. View report
cat results/delay_detail/ExperimentReport.md
```

### Production Results
```bash
# Run full suite (schedule overnight/weekend)
nohup bash ./scripts/run_performance_test.sh full > test.log 2>&1 &

# Monitor progress
tail -f test.log

# Archive results when complete
mkdir -p archive_$(date +%Y%m%d)
mv results/* archive_$(date +%Y%m%d)/
```

---

## Customization Guide

### Testing Lower Latencies (IoT/Edge)
```yaml
Carol_TC_Config:
  Constraint1:
    Type: netem
    Constraint: delay
    StartRange: 1
    EndRange: 50
    Units: ms
    Steps: 10
```

### Testing High-Loss Networks (Satellites/Poor Signal)
```yaml
Carol_TC_Config:
  Constraint1:
    Type: netem
    Constraint: loss
    StartRange: 1
    EndRange: 50
    Units: '%'
    Steps: 10
```

### Testing Realistic WAN (Asymmetric)
```yaml
CoreConfig:
  TC_Iterations: 8

Carol_TC_Config:
  Constraint1:
    Type: netem
    Constraint: delay
    StartRange: 50
    EndRange: 50
    Steps: 1
  Constraint2:
    Type: netem
    Constraint: loss
    StartRange: 2
    EndRange: 2
    Steps: 1

Moon_TC_Config:
  Constraint1:
    Type: netem
    Constraint: delay
    StartRange: 80
    EndRange: 80
    Steps: 1
```

---

## Manual Consolidation

Run the consolidation utility to organize or restore configurations:
```bash
# Preview what will be removed
bash consolidate_configs.sh --dry-run

# Archive old configs
bash consolidate_configs.sh --archive

# Restore an archived config
mv archived_configs/DataCollect_<name>.yaml ./
```

---

## Support

See `CONFIG_REFERENCE.md` for detailed parameter documentation.
See `../README.md` for overall project structure.
