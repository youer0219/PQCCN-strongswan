# 性能测试指南

## 运行模式

### `quick`

用于快速检查环境、容器和最小配置链路：

```bash
python -m pytest -q
bash ./scripts/setup_docker_test_env.sh
bash ./scripts/run_performance_test.sh quick
```

默认使用：
- `configs/experiments/presets/quick_classic_ideal.yaml`
- `configs/experiments/presets/quick_hybrid_ideal.yaml`

### `large`

运行固定的 3 算法 × 4 网络场景矩阵：

```bash
bash ./scripts/run_performance_test.sh large
```

默认算法：
- `Classic-KEX + Classic-Cert`
- `Hybrid(1PQ)-KEX + PQ-Cert`
- `Hybrid(2PQ)-KEX + PQ-Cert`

默认网络场景：
- `ideal:0:0:0`
- `metro:12:2:0.1`
- `wan:68:12:0.6`
- `lossy:135:22:2.0`

## 可调参数

示例：

```bash
bash ./scripts/run_performance_test.sh large \
  --result-dir ./results/perf_large_$(date +%Y%m%d_%H%M) \
  --composite-cases "ideal:0:0:0;metro:12:2:0.1;wan:68:12:0.6;lossy:135:22:2.0:1200" \
  --iterations 200 \
  --warmup-iters 20 \
  --max-time-s 7200
```

`--composite-cases` 格式：
- `name:rtt_ms:jitter_ms:loss_pct[:rate_kbit]`

说明：
- `rtt_ms` 会自动转换为单向 `delay_ms=RTT/2`
- 省略 `rate_kbit` 时表示不限速
- large 模式会自动生成中间 YAML 配置到结果目录下的 `generated_configs/`

## Warmup 行为

预热已集成进主测试流：
- 采集阶段会把预热样本标记为 `IsWarmup=1`
- 统计、绘图和报告会始终排除 warmup 数据

## 图像补生成

`scripts/run_performance_test.sh` 在非 dry-run 模式下会检查：
- `matrix_algo_scenario_p50.svg`
- `matrix_algo_scenario_p95.svg`
- `matrix_algo_scenario_p99.svg`

如果缺失，会基于 `RunLogStatsDF.csv` 自动补生成。

## 推荐验证命令

```bash
python -m pytest -q
python -m pqccn_strongswan --help
python -m pqccn_strongswan.cli.matrix --help
```
