# PQCCN-strongswan
Post-Quantum Cryptography on Constrained Networks

## Data Collection Config Guide

The data collection engine is driven by YAML files in `data_collection/configs`.

### CoreConfig fields

- `TC_Iterations`: Number of IKE setup/traffic/teardown cycles per constraint value.
- `CommandRetries`: Retry count for docker command execution.
- `TrafficCommand`: Traffic command executed inside `carol` per iteration.
- `compose_files`: String or list of compose files.
- `FreshRun`: If `true`, keep existing containers and skip `compose up/down` reset.

### Constraint fields

- `SweepValues`: Explicit list of values to test (overrides Start/End/Steps).
- `SweepMode`: `linear` or `log` (used when SweepValues is not provided).
- `AdjustHost`: `carol`, `moon`, or `both`.
- `AddParams`: Additional tc parameters such as `loss`, `reorder`, `duplicate`, `corrupt`.

### Example

Use `DataCollect_fault_injection_matrix.yaml` to run a mixed condition profile
combining delay, packet loss, reorder, duplicate, and corruption.



License: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
