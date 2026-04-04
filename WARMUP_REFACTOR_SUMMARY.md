# 图像生成重构总结：Warmup数据过滤

## 概述
重构了图像生成流程，使其默认不显示warmup数据，除非明确指定。

## 修改的文件

### 1. **data_analysis/Plotting.py**
- **新增函数**: `_filter_warmup_data(df)` - 过滤warmup数据
- **修改函数**: `PlotVariParam()` - 添加 `include_warmup` 参数（默认为 `False`）
- **行为**: 默认排除所有warmup数据，可以通过参数控制

### 2. **summarize_matrix_results.py**
- **修改函数**: `_prepare_base_table()` - 在数据准备阶段添加warmup过滤
- **过滤条件**:
  - `IsWarmup` 列值为 `1`, `true`, 或 `yes`
  - `ScenarioCase` 列包含 `warmup`（不区分大小写）

### 3. **summarize_results.py**
- **修改函数**: `generate_packet_bytes_from_dataframe()` - 数据处理前过滤warmup
- **功能**: 在计算packet bytes统计之前移除warmup数据

### 4. **reporting.py**
- **新增函数**: `_filter_warmup_from_dataframe(df)` - 通用warmup过滤函数
- **修改函数**: `generate_experiment_report()` - 添加 `include_warmup` 参数（默认为 `False`）
- **功能**: 报告生成时支持控制是否包含warmup数据

### 5. **Orchestration.py**
- **新增参数**: `--include-warmup` - 命令行开关
- **修改**: 将参数传递给 `PlotVariParam()` 和 `generate_experiment_report()`
- **用法**: 
  ```bash
  # 默认行为（排除warmup）
  python3 Orchestration.py ./logs ./configs/config.yaml
  
  # 包含warmup数据
  python3 Orchestration.py ./logs ./configs/config.yaml --include-warmup
  ```

### 6. **data_parsing/ProcessLogs.py** （改进）
- **修改函数**: `Log_stats()` - 增强warmup过滤逻辑
- **过滤条件** (改进后）:
  - 基于 `IsWarmup` 列的值
  - 基于 `ScenarioCase` 列（如果存在）
  - 基于 `VariParam` 列（如果 `ScenarioCase` 不存在）

## 过滤逻辑

### Warmup识别标准
数据行被认为是warmup如果满足以下任一条件：
1. `IsWarmup` 列值为 `'1'`, `'true'`, 或 `'yes'` (不区分大小写）
2. `ScenarioCase` 列包含 `'warmup'` (不区分大小写）

### 过滤流程
1. **数据收集**: warmup在集合阶段执行，标记为 `IsWarmup=1`
2. **数据解析** (ProcessLogs.py): 初始过滤基于 `IsWarmup` 和 `ScenarioCase`
3. **数据分析** (Plotting): 再次过滤确保没有遗漏
4. **报告生成** (reporting.py): 根据 `include_warmup` 参数可选过滤

## 行为变化

### 之前
- Warmup数据出现在报告和图表中
- 示例: "ScenarioCases: ideal, lossy, metro, wan, **warmup**"

### 之后 (默认行为）
- Warmup数据被排除
- 示例: "ScenarioCases: ideal, lossy, metro, wan"
- 使用 `--include-warmup` 恢复旧行为

## 测试验证

已验证以下功能:
```
✓ Warmup数据过滤正确移除了 IsWarmup=True 行
✓ Warmup数据过滤正确移除了 ScenarioCase 包含 'warmup' 的行
✓ PlotVariParam() 正确处理 include_warmup 参数
✓ generate_experiment_report() 正确处理 include_warmup 参数
✓ 报告中选择性地包含/排除warmup数据
✓ 图像中选择性地包含/排除warmup数据
```

## 向后兼容性

- 所有修改都是向后兼容的
- 现有脚本可以继续工作，但需要在调用函数时指定 `include_warmup` 参数
- 命令行工具新增可选参数，默认行为改变为排除warmup

## 使用示例

### Python API
```python
from data_analysis import Plotting
from reporting import generate_experiment_report

# 默认：排除warmup数据
plot_audit = Plotting.PlotVariParam(df, plot_dir, print_level)
report_path = generate_experiment_report(log_dir, df, plot_audit)

# 包含warmup数据
plot_audit = Plotting.PlotVariParam(df, plot_dir, print_level, include_warmup=True)
report_path = generate_experiment_report(log_dir, df, plot_audit, include_warmup=True)
```

### 命令行
```bash
# 默认：排除warmup
python3 Orchestration.py ./logs ./config.yaml

# 包含warmup
python3 Orchestration.py ./logs ./config.yaml --include-warmup
```

## 配置参考

查看各模块中的函数文档字符串了解详细的参数说明：
- `data_analysis/Plotting.py` - `PlotVariParam()` 和 `_filter_warmup_data()`
- `reporting.py` - `generate_experiment_report()` 和 `_filter_warmup_from_dataframe()`
- `Orchestration.py` - `main()` 和参数解析器
