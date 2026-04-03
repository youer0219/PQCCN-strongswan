# PQCCN Performance Test Guide

## 1. 快速开始

安装依赖：

```bash
bash ./scripts/install_python_deps.sh
```

快速验证：

```bash
bash ./scripts/run_performance_test.sh quick
```

统一大规模测试（参数可调）：

```bash
bash ./scripts/run_performance_test.sh large
```

## 2. 仅保留的网络配置集合

当前活动配置仅包含：

### 综合网络画像（4个）
- data_collection/configs/DataCollect_composite_ideal.yaml
- data_collection/configs/DataCollect_composite_metro.yaml
- data_collection/configs/DataCollect_composite_wan.yaml
- data_collection/configs/DataCollect_composite_harsh.yaml

### 快速验证配置（2个）
- data_collection/configs/DataCollect_quick_classic_ideal.yaml
- data_collection/configs/DataCollect_quick_hybrid_ideal.yaml

说明：
- 综合画像按 RTT + 丢包率建模。
- RTT 在执行时按 one-way delay 应用于 netem（delay = RTT / 2）。

## 3. 统一脚本参数（large 模式）

```bash
bash ./scripts/run_performance_test.sh large \
  --result-dir ./results/perf_large_$(date +%Y%m%d_%H%M) \
  --composite-cases "ideal:0:0:4000;metro:20:0.1:3200;wan:60:0.5:2200;harsh:120:2.0:1200" \
  --iterations 8 \
  --warmup-iters 3 \
  --max-time-s 7200
```

`--composite-cases` 格式：
- name:rtt_ms:loss_pct:rate_kbit[:jitter_ms]

## 4. 图像生成保证

统一脚本在测试完成后会检查并确保以下图像生成：
- matrix_latency_percentiles.svg
- matrix_overhead.svg

若缺失，会基于 RunLogStatsDF.csv 自动尝试补生成。

## 5. 结果文件

每次运行目录默认包含：
- ExperimentReport.md
- RunLogStatsDF.csv
- RunLogStatsDF_summary.csv
- PlotAudit.csv
- matrix_latency_percentiles.svg
- matrix_overhead.svg
- packet_bytes.svg（若数据列存在）

## 6. 校验命令

```bash
python3 -m py_compile Orchestration.py data_collection/DataCollectCore.py data_parsing/LogConversion.py scripts/run_crypto_matrix.py summarize_matrix_results.py summarize_results.py
python3 -m unittest discover -s tests -p 'test_*.py'
```
