# 项目结构说明

## 顶层目录

- `src/pqccn_strongswan/`
  主 Python 包。新的实现代码全部放在这里。
- `scripts/`
  命令行辅助脚本，包括快速测试、矩阵测试和环境安装脚本。
- `data_collection/configs/`
  当前维护的 YAML 配置文件。
- `pq-strongswan/`
  Dockerfile、compose 文件、证书和 strongSwan 配置资产。
- `tests/`
  自动化测试。
- `docs/`
  长期维护文档。

## Python 包布局

```text
src/pqccn_strongswan/
├── analysis/
├── collection/
├── parsing/
├── preparation/
├── config_utils.py
├── orchestrator.py
└── reporting.py
```

设计原则：
- 实现代码集中在 `src/`，避免根目录继续堆积脚本模块
- 包内模块文件名使用 snake_case
- 根目录旧入口保留为兼容层，便于旧命令逐步迁移

## 兼容层

以下路径现在主要承担向后兼容职责：
- `Orchestration.py`
- `config_utils.py`
- `reporting.py`
- `summarize_matrix_results.py`
- `summarize_results.py`
- `data_collection/`
- `data_parsing/`
- `data_preparation/`
- `data_analysis/`

这些文件仍可调用，但新代码不应继续把它们当作主实现位置。

## 文档策略

项目文档现在遵循单一事实来源：
- 根 `README.md` 提供项目入口
- `docs/` 提供长期维护说明
- 已移除 `Writerside/` 及其站点配置，避免多套文档并行维护
