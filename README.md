# PQCCN-strongswan

`PQCCN-strongswan` 是一个基于 strongSwan 容器环境的自动化实验流水线，用于对比经典与后量子 IKEv2 方案在受限网络下的连接性能。

当前默认拓扑为 `carol -> moon -> lanhost`：
- `carol`：VPN 客户端，公网侧 `192.168.0.3`
- `moon`：VPN 网关兼内网路由，公网侧 `192.168.0.2`，内网侧 `10.1.0.2`
- `lanhost`：`moon` 后侧内网业务主机，地址 `10.1.0.3`
- `10.3.0.0/24`：客户端通过 IKEv2 获取的虚拟地址池

默认业务流量命令会在建隧后从 `carol` 访问 `lanhost`，不再默认打到网关自身。

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
. ./.venv/bin/activate
```

快速验证：

```bash
python -m pytest -q
bash ./scripts/setup_docker_test_env.sh
bash ./scripts/run_performance_test.sh quick
```

固定矩阵完整测试：

```bash
bash ./scripts/run_performance_test.sh large
```

首次联调建议先完成上面的 `pytest + setup_docker_test_env + quick` 链路，再运行 `large`。

自定义配置集运行：

```bash
python -m pqccn_strongswan \
  ./results/custom_run \
  "./configs/experiments/presets/composite_ideal.yaml,./configs/experiments/presets/composite_wan.yaml"
```

固定矩阵命令也可直接调用：

```bash
pqccn-matrix --result-dir ./results/crypto_matrix
```

## 当前项目结构

- `src/pqccn_strongswan/`: 主 Python 包与实现代码
- `configs/experiments/`: 仓库内维护的 YAML 实验配置
- `scripts/`: 实验执行与环境辅助脚本
- `pq-strongswan/`: strongSwan 容器与证书资产
- `tests/`: 自动化测试
- `docs/`: 使用说明、配置参考与项目结构文档

## 默认实验矩阵

默认算法组合：
- `Classic-KEX + Classic-Cert`
- `Hybrid(1PQ)-KEX + PQ-Cert`
- `Hybrid(2PQ)-KEX + PQ-Cert`

默认网络场景（`rtt/one-way delay/jitter/loss`）：
- `ideal`: `0/0/0/0%`
- `metro`: `15/7.5/1.875/0.05%`
- `wan`: `105/52.5/13.125/0.3%`
- `lossy`: `230/115/28.75/1.0%`

其中：
- `delay_ms = RTT / 2`
- `jitter_ms = RTT / 8`（即单向时延的四分之一）
- `loss_pct` 为双向丢包率，会同时配置到 `Carol` 和 `Moon`

默认 `rate_kbit=-1`，表示不限速。可通过 `--composite-cases` 覆盖矩阵场景。

## 结果输出

每次运行通常会生成：
- `ExperimentReport.md`
- `RunLogStatsDF.csv`
- `RunLogStatsDF_summary.csv`
- `PlotAudit.csv`
- `matrix_algo_scenario_p50.svg`
- `matrix_algo_scenario_p75.svg`
- `matrix_algo_scenario_p90.svg`
- `matrix_algo_scenario_p95.svg`
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
