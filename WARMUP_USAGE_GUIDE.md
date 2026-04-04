# Warmup数据过滤 - 使用指南

## 快速开始

### 默认行为（推荐）
排除所有warmup数据，生成更清晰的分析结果：

```bash
python3 Orchestration.py ./results ./data_collection/configs/config.yaml
```

### 包含warmup数据
如果需要查看warmup辅助数据，使用 `--include-warmup` 参数：

```bash
python3 Orchestration.py ./results ./data_collection/configs/config.yaml --include-warmup
```

## 工作原理

### Warmup识别
系统通过以下方式识别warmup数据：
- **IsWarmup列**: 值为 `1`, `true`, 或 `yes`
- **ScenarioCase列**: 包含关键字 `warmup` (不区分大小写)

### 过滤阶段
Warmup数据在多个阶段被过滤以确保完整性：

1. **数据解析阶段** (`data_parsing/ProcessLogs.py`)
   - 初始识别并移除warmup行

2. **图表生成阶段** (`data_analysis/Plotting.py`, `summarize_*.py`)
   - 再次验证和过滤以防遗漏

3. **报告生成阶段** (`reporting.py`)
   - 根据 `include_warmup` 参数可选过滤

## Python API 使用

### 仅生成图表（默认排除warmup）
```python
from data_analysis import Plotting

# 默认行为：排除warmup
audit_df = Plotting.PlotVariParam(df, './plots', print_level=2)

# 包含warmup
audit_df = Plotting.PlotVariParam(df, './plots', print_level=2, include_warmup=True)
```

### 生成报告（默认排除warmup）
```python
from reporting import generate_experiment_report

# 默认行为：排除warmup
report_path = generate_experiment_report(
    log_dir='./results',
    run_log_stats_df=df,
    plot_audit_df=audit_df
)

# 包含warmup
report_path = generate_experiment_report(
    log_dir='./results',
    run_log_stats_df=df,
    plot_audit_df=audit_df,
    include_warmup=True
)
```

### 手动过滤warmup数据
```python
from data_analysis import Plotting
from reporting import _filter_warmup_from_dataframe

# 使用Plotting模块的过滤函数
filtered_df = Plotting._filter_warmup_data(df)

# 或使用reporting模块的过滤函数
filtered_df = _filter_warmup_from_dataframe(df)
```

## 影响分析

### 报告输出的变化

#### 之前（包含warmup）
```
- ScenarioCases: ideal, lossy, metro, wan, warmup

| ScenarioCase | Algorithm | mean | median | p50 | p95 | p99 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| warmup | Classic-KEX + Classic-Cert | 0.010 | 0.010 | 0.010 | 0.016 | 0.042 |
| ideal | Classic-KEX + Classic-Cert | 0.009 | 0.010 | 0.010 | 0.015 | 0.029 |
| ...
```

#### 之后（默认排除warmup）
```
- ScenarioCases: ideal, lossy, metro, wan

| ScenarioCase | Algorithm | mean | median | p50 | p95 | p99 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ideal | Classic-KEX + Classic-Cert | 0.009 | 0.010 | 0.010 | 0.015 | 0.029 |
| metro | Classic-KEX + Classic-Cert | 0.021 | 0.022 | 0.022 | 0.033 | 0.041 |
| ...
```

### 图表的变化
- **矩阵热力图**: 只显示 4 个网络场景（ideal, metro, wan, lossy），不包含warmup
- **开销百分比图**: 基于实际场景数据，排除warmup基线

## 常见问题

### Q: 为什么默认排除warmup数据？
A: Warmup阶段是为了让系统达到稳定状态，通常不代表生产环境的真实性能。排除它们可以提供更准确的性能分析。

### Q: 如何查看warmup数据的性能？
A: 使用 `--include-warmup` 参数或在Python API中设置 `include_warmup=True`。

### Q: 能否选择性地排除某些warmup？
A: 目前实现的是全部包含或全部排除。要进行更精细的控制，可以：
1. 手动编辑CSV数据
2. 修改过滤函数的条件
3. 使用 `_filter_warmup_data()` 函数创建自定义过滤逻辑

### Q: 已有的结果是否受影响？
A: 不受影响。已生成的CSV和报告保持不变。新的行为仅适用于新运行的分析。

### Q: 如何恢复旧行为？
A: 使用 `--include-warmup` 参数运行Orchestration，或在Python脚本中设置 `include_warmup=True`。

## 技术细节

### 修改的文件
- `data_analysis/Plotting.py` - 核心过滤函数
- `summarize_matrix_results.py` - 矩阵图表生成
- `summarize_results.py` - 数据包比较图表
- `reporting.py` - 报告生成
- `Orchestration.py` - 命令行接口
- `data_parsing/ProcessLogs.py` - 数据解析阶段

### 过滤函数签名
```python
def _filter_warmup_data(df: pd.DataFrame) -> pd.DataFrame:
    """过滤DataFrame中的warmup数据"""
    
def _filter_warmup_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """过滤DataFrame中的warmup数据（报告模块版本）"""
```

## 验证

运行验证脚本确保一切正常：
```bash
python3 test_warmup_refactor.py
```

应该看到所有测试通过的成功消息。

## 更多信息

详见 [WARMUP_REFACTOR_SUMMARY.md](WARMUP_REFACTOR_SUMMARY.md) 了解完整的技术细节。
