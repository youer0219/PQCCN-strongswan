# Unified Network Profile Configuration Reference

## Overview

The collector now uses a unified network profile model.

Supported sections:
- CoreConfig
- Carol_Network_Config
- Moon_Network_Config (optional)

Legacy sections are removed:
- Carol_TC_Config
- Moon_TC_Config

## File Naming

Recommended pattern:
- DataCollect_<scenario>_<modifier>.yaml

Examples:
- DataCollect_composite_ideal.yaml
- DataCollect_composite_metro.yaml
- DataCollect_composite_wan.yaml
- DataCollect_composite_lossy.yaml

## Retained Active Set

Composite network profiles (RTT + loss):
- DataCollect_composite_ideal.yaml
- DataCollect_composite_metro.yaml
- DataCollect_composite_wan.yaml
- DataCollect_composite_lossy.yaml

Quick validation configs:
- DataCollect_quick_classic_ideal.yaml
- DataCollect_quick_hybrid_ideal.yaml

## Top-Level Schema

```yaml
CoreConfig: {}
Carol_Network_Config: {}
Moon_Network_Config: {}
```

Moon_Network_Config is optional.

## CoreConfig Reference

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| TC_Iterations | int | 1 | IKE cycles per profile point |
| MaxTimeS | int | 3600 | Max runtime budget in seconds |
| LocalPath | string | ./ | Optional local output path |
| RemotePath | string | /var/log/charon.log | Container log path |
| CommandRetries | int | 1 | Retry count for failed commands |
| TrafficCommand | string | ping -c 2 10.1.0.2 | Traffic command per cycle |
| PrintLevel | int | 0 | Collector verbosity |
| compose_files | string/list | hybrid2pq compose | Compose files |
| Note | string | "" | Scenario marker written to runstats |
| WarmupIterations | int | 0 | Warm-up cycles |
| WarmupScope | string | per_config | per_config / per_point / off |
| MirrorMoon | bool | false | Apply Carol profile to Moon too |
| FreshRun | bool | false | Reuse existing containers |

## Network Config Reference

### Common Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| Interface | string | no | Network interface, default eth0 |
| AdjustHost | string | no | carol / moon / both |
| SweepKey | string | no | Swept profile dimension |
| SweepValues | list[number] | no | Explicit sweep points |
| StartRange | number | no | Sweep start |
| EndRange | number | no | Sweep end |
| Steps | int | no | Number of sweep steps |
| SweepMode | string | no | linear / log |
| Profile | map | yes | Unified network profile |
| AddParams | string | no | Additional netem parameters |

### Profile Keys

All keys support empty string to indicate no limit.

| Key | Unit | Meaning |
| --- | --- | --- |
| delay_ms | ms | One-way delay |
| jitter_ms | ms | Delay jitter |
| loss_pct | % | Packet loss |
| duplicate_pct | % | Packet duplication |
| corrupt_pct | % | Packet corruption |
| reorder_pct | % | Packet reordering |
| reorder_corr_pct | % | Reorder correlation |
| rate_kbit | kbit | Bandwidth cap |

## Empty Value Semantics

- "" means this dimension is not constrained.
- 0 is treated as no limit as well.
- -1 is treated as no limit as well (recommended for `rate_kbit` in matrix defaults).
- Positive values enable that dimension.

## Fixed Matrix Defaults

The integrated matrix runner uses these defaults:

Algorithms:
- Classic-KEX + Classic-Cert
- Hybrid(1PQ)-KEX + PQ-Cert
- Hybrid(2PQ)-KEX + PQ-Cert

Network scenarios:
- ideal: rtt=0ms, jitter=0ms, loss=0%, rate_kbit=-1
- metro: rtt=12ms, jitter=2ms, loss=0.1%, rate_kbit=-1
- wan: rtt=45ms, jitter=8ms, loss=0.3%, rate_kbit=-1
- lossy: rtt=90ms, jitter=15ms, loss=1.0%, rate_kbit=-1

Default sampling counts:
- WarmupIterations: 20
- TC_Iterations (formal): 200

Warmup behavior:
- Warmup is executed inside the same collection flow and written into runstats metadata.
- Warmup rows are marked with `IsWarmup=1` and excluded during final statistics aggregation.

## Sweep Rules

- Without SweepKey: single static profile point.
- With SweepKey + SweepValues: iterate explicit values.
- With SweepKey + Start/End/Steps: auto-generate points.

Current behavior:
- Carol sweep is supported.
- Moon is static in one run.

## Example: Delay Sweep with Static Loss

```yaml
Carol_Network_Config:
  Interface: eth0
  AdjustHost: carol
  SweepKey: delay_ms
  SweepValues: [1, 20, 50, 100]
  Profile:
    delay_ms: ""
    jitter_ms: 2
    loss_pct: 0.5
    duplicate_pct: ""
    corrupt_pct: ""
    reorder_pct: ""
    reorder_corr_pct: ""
    rate_kbit: ""
```

## Example: Baseline (No Network Limits)

```yaml
Carol_Network_Config:
  Interface: eth0
  AdjustHost: carol
  Profile:
    delay_ms: ""
    jitter_ms: ""
    loss_pct: ""
    duplicate_pct: ""
    corrupt_pct: ""
    reorder_pct: ""
    reorder_corr_pct: ""
    rate_kbit: ""
```

## Logging and Metadata

Each point writes:
- profile-based log filename (full network signature)
- runstats fields:
  - ScenarioNote
  - SweepKey
  - NetworkProfile
  - CarolProfile
  - MoonProfile
  - tc_command

## Migration Checklist (from old schema)

1. Remove Carol_TC_Config/Moon_TC_Config.
2. Add Carol_Network_Config with Profile keys.
3. Move old delay/loss/rate values into Profile or sweep fields.
4. Use empty string for dimensions you do not want to constrain.

