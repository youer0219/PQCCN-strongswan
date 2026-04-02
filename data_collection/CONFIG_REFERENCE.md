# IPsec Performance Test Configuration Reference

## Configuration File Organization

This directory contains YAML configuration files that define test scenarios for the IPsec performance testing framework.

### Naming Convention

Configurations follow the pattern: `DataCollect_[SCENARIO]_[MODIFIER].yaml`

- **SCENARIO**: Test type (baseline, delay, loss, rate, fault_injection_matrix)
- **MODIFIER**: Optional (quick, DH, PQ, extensive)

### Quick Start Configs (5-10 minutes)

| File | Purpose | Steps | Iterations |
|------|---------|-------|-----------|
| `DataCollect_baseline_quick.yaml` | Baseline performance (no network faults) | 1 | 3 |
| `DataCollect_delay_quick.yaml` | Delay impact (1/100/200ms) | 3 | 3 |
| `DataCollect_fault_quick.yaml` | Combined faults (1% loss + 0.5% dup) | 2 | 3 |

### Full Test Configs (3-4 hours total)

| File | Scenario | Steps | Iterations | Test Range |
|------|----------|-------|-----------|------------|
| `DataCollect_baseline.yaml` | Baseline performance | 1 | 10 | — |
| `DataCollect_delay.yaml` | Delay sweep | 5 | 10 | 1-200ms |
| `DataCollect_pktLoss.yaml` | Packet loss sweep | 5 | 10 | 0.1%-25% |
| `DataCollect_rate_PQ.yaml` | Bandwidth rate limiting | 21 | 10 | 128-4 kbps |
| `DataCollect_fault_injection_matrix.yaml` | Multi-fault combinations | 8 | 12 | Multiple |

---

## Configuration Structure

### CoreConfig Section
```yaml
CoreConfig:
  TC_Iterations: 10         # Tunnel setup/teardown cycles per constraint value
  MaxTimeS: 36000           # Maximum test duration (seconds)
  LocalPath: "../../"       # Local directory for log storage
  RemotePath: "/var/log/charon.log"  # Remote log file path in container
  CommandRetries: 2         # Retry failed commands this many times
  TrafficCommand: "ping -c 2 10.1.0.2"  # Optional traffic during tunnel establishment
  PrintLevel: 1             # Verbosity: 0=silent, 1=normal, 2=verbose
  compose_files: "./pq-strongswan/hybrid2pq-docker-compose.yml"
  Note: "Test description"  # Metadata tag for results
```

### Traffic Control (TC) Constraint Sections
```yaml
Carol_TC_Config:
  Constraint1:
    Type: netem              # Network emulation constraint
    Constraint: delay        # Type: delay, loss, duplicate, corrupt, reorder, rate
    Interface: eth0          # Network interface
    StartRange: 1            # Minimum value
    EndRange: 200            # Maximum value
    Units: ms                # ms, %, kbps (depends on constraint)
    Steps: 5                 # Number of sweep steps
    AddParams: ''            # Additional tc parameters
```

### Algorithm Configuration
```yaml
AlgoParam:
  Baseline: false            # If true: baseline (DH) only; false: post-quantum only
                            # Omit for auto-detect from log analysis
```

### Sweep Modes
```yaml
SweepMode: linear            # linear sweep (default) or log (logarithmic)
SweepValues: [1, 10, 100]   # Explicit values (overrides StartRange/EndRange/Steps)
```

---

## Parameter Reference

### TC Constraint Types

| Constraint | Units | Typical Range | Notes |
|------------|-------|---------------|-------|
| **delay** | ms | 1-500 | Network latency |
| **loss** | % | 0.1-25 | Packet loss rate |
| **duplicate** | % | 0.1-10 | Duplicate packet rate |
| **corrupt** | % | 0.1-5 | Corrupt packet rate |
| **reorder** | % | 0.1-10 | Packet reordering rate |
| **rate** | kbps | 64-4000 | Bandwidth limiting |

### recommended Values for Post-Quantum Testing

#### Delay Scenarios
- **Ultra-low latency**: 1-10ms
- **LAN/local**: 1-50ms
- **WAN/typical**: 10-200ms
- **Satellite/poor**: 200-500ms

#### Loss Scenarios
- **Excellent**: 0.1-0.5%
- **Good**: 0.5-1%
- **Fair**: 1-5%
- **Poor**: 5-25%

#### Bandwidth Scenarios
- **High-speed**: 1-10 Mbps (1000-10000 kbps)
- **Broadband**: 10-100 Mbps
- **Mobile 4G**: 5-50 Mbps
- **Mobile 3G**: 1-10 Mbps
- **Poor/satellite**: 256kbps-2Mbps (256-2000 kbps)
- **Extreme**: 64-256 kbps

---

## Creating New Configurations

### Template
```yaml
---
CoreConfig:
  TC_Iterations: 10          # Adjust per testing needs
  MaxTimeS: 36000            # Adjust per test duration estimate
  LocalPath: "../../"
  RemotePath: "/var/log/charon.log"
  CommandRetries: 2
  TrafficCommand: "ping -c 2 10.1.0.2"
  PrintLevel: 1
  compose_files: "./pq-strongswan/hybrid2pq-docker-compose.yml"
  Note: "YOUR_TEST_DESCRIPTION"

Carol_TC_Config:
  Constraint1:
    Type: netem
    Constraint: delay        # Modify for your test
    Interface: eth0
    StartRange: 1
    EndRange: 100
    Units: ms
    Steps: 5
    AddParams: ''
```

### Conservative Estimates for Duration Calculation
```
Duration ≈ (TC_Iterations × Steps × 3-4 sec/cycle) + 30sec overhead

Examples:
- DataCollect_baseline_quick: 3 × 1 × 3 + 30 = ~40 sec
- DataCollect_delay_quick: 3 × 3 × 3 + 30 = ~60 sec
- DataCollect_delay.yaml: 10 × 5 × 4 + 30 = ~240 sec (~4 min)
```

---

## Configuration Usage

### Automatic Detection of All Configs
```bash
python3 Orchestration.py ./results ./data_collection/configs/
```

### Single Config
```bash
python3 Orchestration.py ./results ./data_collection/configs/DataCollect_delay.yaml
```

### Multiple Specific Configs
```bash
python3 Orchestration.py ./results "baseline.yaml,delay.yaml,loss.yaml"
```

### Wildcard (All Quick Configs)
```bash
python3 Orchestration.py ./results "./data_collection/configs/*quick.yaml"
```

---

## Common Configuration Patterns

### Multi-Fault Injection (Realistic Network)
```yaml
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
    StartRange: 1
    EndRange: 1
    Steps: 1
  Constraint3:
    Type: netem
    Constraint: duplicate
    StartRange: 0.5
    EndRange: 0.5
    Steps: 1
```

### Logarithmic Bandwidth Sweep
```yaml
SweepMode: log
Carol_TC_Config:
  Constraint1:
    Type: netem
    Constraint: rate
    StartRange: 64
    EndRange: 4096
    Units: kbps
    Steps: 7
```

---

## Maintenance & Best Practices

1. **Keep quick variants** for rapid development iteration
2. **Use descriptive Note fields** for experiment tracking
3. **Document custom AddParams** in config comments
4. **Version control** parameters for reproducibility
5. **Archive results** with corresponding config files

## Notes

- All times are in seconds unless specified
- All paths are relative to workspace root
- TC_Iterations directly affects test duration; use 3-5 for validation, 10+ for production
- TrafficCommand is optional; use for increased packet throughput testing
- MirrorMoon copies Carol's TC settings to Moon side if true
