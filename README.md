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

## Setup

Let's walk through building the docker container and installing required python modules.


1. Open a terminal console
2. Optional: Navigate to the pq-strongswan folder and build the image manually.Use the command: `docker build -t strongx509/pq-strongswan:latest .`
   > If the image `strongx509/pq-strongswan:latest` does not exist in the local Docker host, Docker will automatically attempt to pull it from Docker Hub. This is also reliable.
3. Install Python dependencies: `pip install numpy python-on-whales pyyaml tqdm`
   > If you are using a Python virtual environment, be sure to activate that environment before installing the modules.
   > You can also try running `pip install -r settings.txt`.
4. Run `python3 ./Orchestration.py <LOG_DIR> <CONFIG_INPUT>`
   - `<CONFIG_INPUT>` supports a single YAML, a directory, wildcard, or comma-separated list.
   - Example: `python3 ./Orchestration.py ./results "./data_collection/configs/*.yaml"`

## Fast Test Environment Setup

The repository now includes scripts for quick local test bootstrapping:

1. Install Python dependencies:
   `bash ./scripts/install_python_deps.sh`
2. Prepare and start Docker test environment:
   `bash ./scripts/setup_docker_test_env.sh`
3. Run orchestration with an advanced fault-injection profile:
   `python3 ./Orchestration.py <LOG_DIR> ./data_collection/configs/DataCollect_fault_injection_matrix.yaml`
4. Run a full suite quickly:
   `bash ./scripts/run_experiment_suite.sh <OUTPUT_DIR> "./data_collection/configs/*.yaml"`

After each orchestration run, the result directory includes:

- `ExperimentReport.md`: one-page summary report
- `PlotAudit.csv`: plot sanity audit table
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


License: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
