# 快速上手

## 前置条件

- Docker
- Python 3.9+

## 安装

项目已切换为标准 `src/` 包布局，推荐先安装为 editable package：

```bash
bash ./scripts/install_python_deps.sh
```

该脚本会执行：

```bash
python3 -m pip install -e .
```

## 最常用命令

快速验证：

```bash
bash ./scripts/run_performance_test.sh quick
```

固定矩阵实验：

```bash
bash ./scripts/run_performance_test.sh large
```

直接调用主编排入口：

```bash
python3 -m pqccn_strongswan \
  ./results/manual_run \
  ./configs/experiments/presets/composite_ideal.yaml
```

一次运行多个配置：

```bash
python3 -m pqccn_strongswan \
  ./results/custom_run \
  "./configs/experiments/presets/composite_ideal.yaml,./configs/experiments/presets/composite_wan.yaml"
```

## 结果目录

一次运行结束后，结果目录通常包含：
- `ExperimentReport.md`
- `RunLogStatsDF.csv`
- `RunLogStatsDF_summary.csv`
- `PlotAudit.csv`
- `matrix_*.svg`
- `packet_bytes.svg`（如果数据列存在）

## 当前入口

推荐入口：
- `python3 -m pqccn_strongswan`
- `pqccn-matrix`
- `src/pqccn_strongswan/` 下的包模块
