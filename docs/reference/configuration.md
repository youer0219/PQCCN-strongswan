# 配置参考

## 当前保留的配置文件

### 固定网络画像

- `data_collection/configs/DataCollect_composite_ideal.yaml`
- `data_collection/configs/DataCollect_composite_metro.yaml`
- `data_collection/configs/DataCollect_composite_wan.yaml`
- `data_collection/configs/DataCollect_composite_lossy.yaml`

### 快速验证

- `data_collection/configs/DataCollect_quick_classic_ideal.yaml`
- `data_collection/configs/DataCollect_quick_hybrid_ideal.yaml`

### 模板

- `data_collection/configs/DataCollect_TEMPLATE.yaml`

历史配置仍保存在：
- `data_collection/configs/archived_configs/`

## 统一配置模型

当前采集器只支持统一网络画像结构：

```yaml
CoreConfig: {}
Carol_Network_Config: {}
Moon_Network_Config: {}
```

不再支持旧版：
- `Carol_TC_Config`
- `Moon_TC_Config`

## `CoreConfig`

常用字段：

| 字段 | 说明 |
| --- | --- |
| `TC_Iterations` | 每个画像点的正式采样次数 |
| `MaxTimeS` | 单个配置的最大运行时长 |
| `RemotePath` | 容器内 strongSwan 日志路径 |
| `CommandRetries` | 命令失败后的重试次数 |
| `TrafficCommand` | 每轮 IKE 建连后执行的业务流量命令 |
| `compose_files` | 使用的 docker compose 文件 |
| `Note` | 场景标签，写入 runstats 元数据 |
| `WarmupIterations` | 预热次数 |
| `WarmupScope` | `per_config` / `per_point` / `off` |

## `Carol_Network_Config` / `Moon_Network_Config`

常用字段：

| 字段 | 说明 |
| --- | --- |
| `Interface` | 默认 `eth0` |
| `AdjustHost` | `carol` / `moon` / `both` |
| `SweepKey` | 要 sweep 的网络维度 |
| `SweepValues` | 显式 sweep 点列表 |
| `StartRange` / `EndRange` / `Steps` | 自动生成 sweep 点 |
| `Profile` | 统一网络画像 |
| `AddParams` | 附加 netem 参数 |

## `Profile` 字段

| 字段 | 单位 | 含义 |
| --- | --- | --- |
| `delay_ms` | ms | 单向时延 |
| `jitter_ms` | ms | 抖动 |
| `loss_pct` | % | 丢包率 |
| `duplicate_pct` | % | 重复包比例 |
| `corrupt_pct` | % | 损坏包比例 |
| `reorder_pct` | % | 乱序比例 |
| `reorder_corr_pct` | % | 乱序相关性 |
| `rate_kbit` | kbit | 带宽限制 |

约定：
- 空字符串 `""` 表示该维度不限制
- `0` 或 `-1` 在当前实现里也会被视为“不生效”

## 最小示例

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
