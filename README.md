# PQCCN-strongswan

PQCCN-strongswan 是一个基于 strongSwan 容器环境的自动化实验流水线，用于对比经典与后量子 IKEv2 方案在受限网络下的连接性能。

项目主页：<a target="_blank" rel="noreferrer noopener" href="https://jfluhler.github.io/PQCCN-strongswan/">GitHub Pages</a>

## 核心变化（2026-04）

- 全面切换为统一综合网络配置：`Carol_Network_Config` / `Moon_Network_Config`
- 允许网络字段留空，表示该维度不限制
- 日志命名绑定“全量网络画像”，不再只绑定 delay
- 图表 detail 不再硬编码 delay 字段

## 快速开始

前置条件：
- Docker
- Python 3

安装 Python 依赖：

```bash
bash ./scripts/install_python_deps.sh
```

快速验证（约 5-10 分钟）：

```bash
bash ./scripts/run_performance_test.sh quick
```

完整测试（约 3-4 小时）：

```bash
bash ./scripts/run_performance_test.sh large
```

自定义配置集运行：

```bash
python3 Orchestration.py ./results/custom_run "./data_collection/configs/DataCollect_composite_ideal.yaml,./data_collection/configs/DataCollect_composite_wan.yaml"
```

## 配置模型（统一网络画像）

每个网络配置文件使用以下结构：

```yaml
CoreConfig:
  TC_Iterations: 10
  MaxTimeS: 36000
  RemotePath: "/var/log/charon.log"
  compose_files: "./pq-strongswan/hybrid2pq-docker-compose.yml"
  Note: "example"

Carol_Network_Config:
  Interface: eth0
  AdjustHost: carol
  SweepKey: delay_ms
  SweepValues: [1, 20, 50, 100]
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

说明：
- `Profile` 中字段为空字符串表示该项不限制
- 通过 `SweepKey` + `SweepValues` 对某一维做 sweep
- 未设置 `SweepKey` 时按单点静态画像运行

## 输出目录

每次运行会生成一个结果目录，典型文件如下：

- `ExperimentReport.md`：实验摘要
- `RunLogStatsDF.csv`：全量统计
- `RunLogStatsDF_summary.csv`：摘要视图
- `PlotAudit.csv`：图形审计信息
- `matrix_latency_percentiles.svg`：矩阵分位数图
- `matrix_overhead.svg`：矩阵开销图
- `packet_bytes.svg`：可选报文大小图

## 主要脚本入口

- `scripts/run_performance_test.sh`：quick/large 统一脚本（large 模式可调参数）
- `scripts/run_experiment_suite.sh`：批量实验入口
- `scripts/run_crypto_matrix.py`：三种密码学场景矩阵实验
- `Orchestration.py`：端到端主编排（采集→解析→制表→绘图→报告）

## 文档导航

- [PERFORMANCE_TEST_GUIDE.md](PERFORMANCE_TEST_GUIDE.md)
- [data_collection/CONFIG_REFERENCE.md](data_collection/CONFIG_REFERENCE.md)
- [data_collection/configs/README.md](data_collection/configs/README.md)
- [data_collection/README.md](data_collection/README.md)

License: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
