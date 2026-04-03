# Data Collection Module

本模块负责执行容器编排、网络画像施加、日志抓取以及运行元数据记录。

## 统一配置结构

采集配置现在只支持统一网络画像模型：

- `CoreConfig`
- `Carol_Network_Config`
- `Moon_Network_Config`（可选）

不再支持旧版 `Carol_TC_Config` / `Moon_TC_Config`。

## 关键字段

### CoreConfig

- `TC_Iterations`：每个画像点的循环次数
- `MaxTimeS`：最大运行时长
- `CommandRetries`：命令重试次数
- `TrafficCommand`：每轮流量命令
- `compose_files`：docker compose 文件
- `Note`：场景标签

### Carol_Network_Config / Moon_Network_Config

- `Interface`：网卡名称，通常为 `eth0`
- `AdjustHost`：`carol` / `moon` / `both`
- `SweepKey`：要做 sweep 的画像维度（可省略）
- `SweepValues` 或 `StartRange/EndRange/Steps`：sweep 定义
- `Profile`：综合网络字段
	- `delay_ms`
	- `jitter_ms`
	- `loss_pct`
	- `duplicate_pct`
	- `corrupt_pct`
	- `reorder_pct`
	- `reorder_corr_pct`
	- `rate_kbit`
- `AddParams`：附加 netem 参数（可选）

约定：`Profile` 中字段留空（`""`）表示该网络维度不限制。

## 日志与画像绑定

- 日志文件名基于完整网络画像签名生成
- `runstats.txt` 中写入 `NetworkProfile` / `CarolProfile` / `MoonProfile` / `SweepKey`
- 后续解析和图表直接消费这些字段

## 示例

参考：
- `data_collection/configs/DataCollect_TEMPLATE.yaml`
- `data_collection/configs/DataCollect_composite_ideal.yaml`

License: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
