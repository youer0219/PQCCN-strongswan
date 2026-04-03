# Configuration Files

This directory now keeps a minimal active set.

## Retained Active Configs

### Composite Network Profiles (RTT + loss)
- DataCollect_composite_ideal.yaml
- DataCollect_composite_metro.yaml
- DataCollect_composite_wan.yaml
- DataCollect_composite_harsh.yaml

### Quick Validation
- DataCollect_quick_classic_ideal.yaml
- DataCollect_quick_hybrid_ideal.yaml

### Template
- DataCollect_TEMPLATE.yaml

Other former active configs were removed from the active set and are no longer considered by default workflows.

## Schema

All active files use:
- CoreConfig
- Carol_Network_Config
- Moon_Network_Config (optional)

Legacy sections are not supported:
- Carol_TC_Config
- Moon_TC_Config

## Usage

Quick check:

```bash
bash ./scripts/run_performance_test.sh quick
```

Unified large-scale run (parameterized):

```bash
bash ./scripts/run_performance_test.sh large --composite-cases "ideal:0:0:4000;metro:20:0.1:3200;wan:60:0.5:2200;harsh:120:2.0:1200" --iterations 8
```

Run explicit active profile list:

```bash
python3 Orchestration.py ./results/profiles "./data_collection/configs/DataCollect_composite_ideal.yaml,./data_collection/configs/DataCollect_composite_metro.yaml,./data_collection/configs/DataCollect_composite_wan.yaml,./data_collection/configs/DataCollect_composite_harsh.yaml"
```

## Note

RTT values are represented as one-way delay in profile files:
- delay_ms = RTT / 2
