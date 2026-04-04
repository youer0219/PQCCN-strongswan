# 项目结构说明

## 顶层目录

- `src/pqccn_strongswan/`
  主 Python 包。新的实现代码全部放在这里。
- `configs/experiments/`
  仓库内维护的 YAML 配置、模板和历史归档。
- `scripts/`
  命令行辅助脚本，包括快速测试、矩阵测试和环境安装脚本。
- `pq-strongswan/`
  Dockerfile、compose 文件、证书和 strongSwan 配置资产。
- `tests/`
  自动化测试。
- `docs/`
  长期维护文档。

## Python 包布局

```text
src/pqccn_strongswan/
├── cli/
├── collection/
├── config/
├── processing/
└── reporting/
```

设计原则：
- 实现代码集中在 `src/`，避免根目录继续堆积脚本模块
- 配置资产收敛到 `configs/experiments/`，避免与 Python 包命名耦合
- 包内模块文件名使用 snake_case
- 仓库根目录不再保留 Python shim 或旧式 `data_*` 包

## 文档策略

项目文档现在遵循单一事实来源：
- 根 `README.md` 提供项目入口
- `docs/` 提供长期维护说明
- 已移除 `Writerside/` 及其站点配置，避免多套文档并行维护
