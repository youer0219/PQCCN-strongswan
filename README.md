# PQCCN-strongswan

`PQCCN-strongswan` 是一个基于 strongSwan 容器环境的自动化实验流水线，用于对比经典与后量子 IKEv2 方案在受限网络下的连接性能。

仓库现已完成两项整理：
- Python 代码收敛到标准 `src/` 包布局，主包为 `pqccn_strongswan`
- 原 `Writerside/` 文档站已移除，长期维护文档统一收敛到 [`docs/`](docs/README.md)

## 快速开始

前置条件：
- Docker
- Python 3.9+

安装项目与依赖：

```bash
bash ./scripts/install_python_deps.sh
```

快速验证：

```bash
bash ./scripts/run_performance_test.sh quick
```

固定矩阵完整测试：

```bash
bash ./scripts/run_performance_test.sh large
```

自定义配置集运行：

```bash
python3 -m pqccn_strongswan \
  ./results/custom_run \
  "./data_collection/configs/DataCollect_composite_ideal.yaml,./data_collection/configs/DataCollect_composite_wan.yaml"
```

## 当前项目结构

- `src/pqccn_strongswan/`: 主 Python 包与实现代码
- `scripts/`: 实验执行与环境辅助脚本
- `data_collection/configs/`: 当前保留的 YAML 配置集
- `pq-strongswan/`: strongSwan 容器与证书资产
- `tests/`: 自动化测试
- `docs/`: 使用说明、配置参考与项目结构文档

兼容性说明：
- 根目录的 `Orchestration.py`、`reporting.py`、`summarize_*.py` 以及 `data_*` 目录仍保留为薄兼容层
- 新增开发应优先使用 `src/pqccn_strongswan/` 下的实现与 `python3 -m pqccn_strongswan`

## 默认实验矩阵

默认算法组合：
- `Classic-KEX + Classic-Cert`
- `Hybrid(1PQ)-KEX + PQ-Cert`
- `Hybrid(2PQ)-KEX + PQ-Cert`

默认网络场景（`rtt/jitter/loss`）：
- `ideal`: `0/0/0%`
- `metro`: `12/2/0.1%`
- `wan`: `68/12/0.6%`
- `lossy`: `135/22/2.0%`

默认 `rate_kbit=-1`，表示不限速。可通过 `--composite-cases` 覆盖矩阵场景。

## 结果输出

每次运行通常会生成：
- `ExperimentReport.md`
- `RunLogStatsDF.csv`
- `RunLogStatsDF_summary.csv`
- `PlotAudit.csv`
- `matrix_algo_scenario_p50.svg`
- `matrix_algo_scenario_p95.svg`
- `matrix_algo_scenario_p99.svg`
- `matrix_latency_percentiles.svg`
- `matrix_overhead_percentiles.svg`
- `packet_bytes.svg`（当数据列存在时）

## 文档导航

- [文档索引](docs/README.md)
- [快速上手](docs/guides/getting-started.md)
- [性能测试指南](docs/guides/performance-testing.md)
- [配置参考](docs/reference/configuration.md)
- [项目结构说明](docs/reference/project-structure.md)

License: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
