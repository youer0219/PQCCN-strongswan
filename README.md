# PQCCN-strongswan
pq-strongswan wrapper for data collection and analysis. Advancing IKEv2 for the Quantum Age: Challenges in Post-Quantum Cryptography Implementation on Constrained Network

For full documentation refer to the <a target="_blank" rel="noreferrer noopener" href="https://jfluhler.github.io/PQCCN-strongswan/">Project Github Pages</a>

# Quick Setup Guide

The data-collection part of this project operates like a wrapper to the
[strongX509/pq-strongswan](https://github.com/strongX509/docker/tree/master/pq-strongswan)
docker container. However, there are some modification from the pq-strongswan base repository. 
We want to specially note that the work by [Andreas Steffen](https://github.com/strongX509) in making the pq-strongswan repo was of great help in starting this project. The core of his efforts are at the core of this project.

## Before you start

The following pre-requisites that are required to use this project.
- Docker
- Python 3

## Quick Commands

### For Rapid Testing (5-10 minutes)
```bash
bash ./scripts/run_performance_test.sh quick
```

### For Comprehensive Analysis (3-4 hours)
```bash
bash ./scripts/run_performance_test.sh full
```

### For Custom Test Scenarios
```bash
# Single config
python3 Orchestration.py ./results/test_name ./data_collection/configs/DataCollect_delay.yaml

# Directory (all configs)
python3 Orchestration.py ./results/batch ./data_collection/configs/

# Wildcard (specific pattern)
python3 Orchestration.py ./results/quick "./data_collection/configs/*quick.yaml"

# Comma-separated (explicit selection)
python3 Orchestration.py ./results/custom "baseline.yaml,delay.yaml"
```

## Output

After each test run, results are saved to a timestamped directory with:
- `ExperimentReport.md` - One-page summary with key metrics and plot audit
- `PlotAudit.csv` - Plot quality sanity checks
- `RunLogStatsDF.csv` - Complete performance statistics
- `*.png` - Comparison plots with trend lines and error bands
- `RunLogStatsDF.csv`: merged run statistics
- `RunLogStatsDF_summary.csv`: compact summary view

## Testing Optimization Notes

Recent improvements focus on four goals:

1. More diverse fault injection conditions:
   - `SweepValues` supports explicit non-linear test points.
   - `SweepMode` supports `linear` and `log` sweeps.
   - `AdjustHost` can target `carol`, `moon`, or `both`.
   - `AddParams` can combine delay/loss/reorder/duplicate/corrupt in one profile.

2. More robust collection code:
   - Config parsing now validates required sections and normalizes fields.
   - Docker command execution uses retries (`CommandRetries`).
   - Cleanup is guaranteed by `finally` logic even after runtime errors.
   - `TrafficCommand` is configurable for custom traffic generation.

3. Better image generation:
   - Numeric extraction now supports decimal values.
   - Plots include scatter + trend line + standard deviation ribbon.
   - Output naming is sanitized for filesystem safety.
   - Axis scaling is more stable across sparse and dense test runs.

4. Better test configurations:
   - `requirements.txt` added for deterministic Python setup.
   - `DataCollect_fault_injection_matrix.yaml` added as a richer template.

***You did it! The required resources are now installed!***

## Documentation

All comprehensive documentation is now available in English:

- **[PERFORMANCE_TEST_GUIDE.md](PERFORMANCE_TEST_GUIDE.md)** - Complete testing guide with exact commands, timing breakdown, test scenarios, and troubleshooting
- **[data_collection/CONFIG_REFERENCE.md](data_collection/CONFIG_REFERENCE.md)** - Detailed configuration parameter reference and real-world scenario patterns
- **[data_collection/configs/README.md](data_collection/configs/README.md)** - Configuration file organization, usage examples, and customization guide
- **[Writerside/](Writerside/)** - Full technical documentation in Writerside format

License: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
