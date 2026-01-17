# 加密货币行情监控告警系统 - 验收规格文档

**版本**: 1.0
**日期**: 2026-01-17
**项目代号**: Signal

---

## 1. 项目概述

### 1.1 项目目标
构建一个基于 Python 的实时加密货币行情监控系统，通过 CCXT WebSocket 订阅多交易所市场数据，计算技术指标，在满足特定条件时向飞书（Lark）推送告警消息。

### 1.2 核心价值
- **实时监控**: WebSocket 实时数据流，低延迟捕捉市场机会
- **智能过滤**: 多维度技术指标组合，减少噪音告警
- **灵活配置**: YAML 配置文件管理交易所、市场和告警参数
- **高可用性**: 自动重连机制，并行多交易所订阅

---

## 2. 功能性需求

### 2.1 数据订阅层 (F-01)
**需求描述**: 使用 CCXT Pro WebSocket API 订阅 15 分钟 K 线数据

**验收标准**:
- ✅ 支持同时订阅多个交易所（Binance, OKX, Bybit 等）
- ✅ 支持每个交易所订阅多个交易对（如 BTC/USDT, ETH/USDT）
- ✅ 使用 asyncio 实现并行订阅，各交易所独立连接
- ✅ WebSocket 断线自动重连（最大重试 5 次，指数退避策略）
- ✅ 实时接收 15 分钟 K 线更新事件

**测试场景**:
```python
# TC-F01-01: 单交易所单市场订阅
配置: Binance BTC/USDT
预期: 成功建立 WebSocket 连接，接收 K 线数据

# TC-F01-02: 多交易所并行订阅
配置: Binance BTC/USDT + OKX ETH/USDT
预期: 两个连接同时建立，数据独立处理

# TC-F01-03: 断线重连
操作: 手动断开网络连接
预期: 5 秒内自动重连，数据流恢复
```

---

### 2.2 技术指标计算引擎 (F-02)
**需求描述**: 内存中计算 MA30、成交量异常、价格新高新低

**验收标准**:
- ✅ **MA30 计算**: 简单移动平均（SMA），基于收盘价，窗口 30 根 K 线
- ✅ **成交量异常**: 当前 15 分钟成交量 >= 前 4 根 K 线（1 小时）平均值的 3 倍
- ✅ **1 小时新高**: 当前价格 > 最近 4 根 K 线的最高价
- ✅ **1 小时新低**: 当前价格 < 最近 4 根 K 线的最低价
- ✅ 使用滑动窗口，最多保留 100 根 K 线数据（内存优化）
- ✅ 数据不足时不触发告警（如启动初期 < 30 根 K 线）

**计算公式**:
```python
# MA30 (Simple Moving Average)
MA30 = sum(close[-30:]) / 30

# 成交量异常判断
avg_volume_1h = sum(volume[-4:-1]) / 3  # 前 3 根 K 线平均值
is_volume_surge = volume[-1] >= avg_volume_1h * 3.0

# 新高新低判断
high_1h = max(high[-4:-1])  # 前 3 根 K 线最高价
low_1h = min(low[-4:-1])    # 前 3 根 K 线最低价
is_new_high = close[-1] > high_1h and close[-1] > MA30
is_new_low = close[-1] < low_1h and close[-1] < MA30
```

**测试场景**:
```python
# TC-F02-01: MA30 计算准确性
输入: 30 根 K 线收盘价 [100, 101, 102, ..., 129]
预期: MA30 = 114.5

# TC-F02-02: 成交量异常检测
输入: volume = [1000, 1000, 1000, 4000]
预期: is_volume_surge = True (4000 >= 1000 * 3)

# TC-F02-03: 新高新低检测
输入: high = [100, 101, 102, 105], close = 106, MA30 = 100
预期: is_new_high = True

# TC-F02-04: 数据不足不触发
输入: 仅 10 根 K 线数据
预期: 不计算 MA30，不触发告警
```

---

### 2.3 告警条件判断引擎 (F-03)
**需求描述**: 三个条件同时满足才触发告警

**验收标准**:
- ✅ **条件 1**: 成交量突然放大（>= 3 倍前 1 小时均值）
- ✅ **条件 2a**: 价格在 MA30 以上 **且** 突破 1 小时新高（看涨信号）
- ✅ **条件 2b**: 价格在 MA30 以下 **且** 突破 1 小时新低（看跌信号）
- ✅ 逻辑关系: `条件1 AND (条件2a OR 条件2b)`
- ✅ 冷却期机制: 同一市场触发后 5 分钟内不再告警

**决策树**:
```
成交量放大? ──No──> 不告警
    │
   Yes
    │
价格 > MA30? ──Yes──> 是否新高? ──Yes──> 触发告警
    │                      │
   No                     No ──> 不告警
    │
价格 < MA30? ──Yes──> 是否新低? ──Yes──> 触发告警
    │                      │
   No                     No ──> 不告警
```

**测试场景**:
```python
# TC-F03-01: 看涨信号触发
输入: volume_surge=True, close=110, MA30=100, new_high=True
预期: 触发告警，类型=看涨

# TC-F03-02: 看跌信号触发
输入: volume_surge=True, close=90, MA30=100, new_low=True
预期: 触发告警，类型=看跌

# TC-F03-03: 缺少成交量条件
输入: volume_surge=False, close=110, MA30=100, new_high=True
预期: 不触发告警

# TC-F03-04: 价格在 MA30 附近但无突破
输入: volume_surge=True, close=101, MA30=100, new_high=False
预期: 不触发告警

# TC-F03-05: 冷却期内重复触发
操作: 同一市场 3 分钟内第二次满足条件
预期: 不推送消息，日志记录"冷却期内"
```

---

### 2.4 飞书消息推送 (F-04)
**需求描述**: 通过 Lark Webhook 推送格式化告警消息

**验收标准**:
- ✅ 使用飞书机器人 Webhook URL（从配置文件读取）
- ✅ 消息格式为富文本卡片（支持 Markdown）
- ✅ 包含必要信息: 交易所、市场、价格、涨跌幅、指标缩写
- ✅ 推送失败时记录错误日志，不中断监控流程
- ✅ 支持消息限流（可选：每分钟最多推送 10 条）

**消息模板**:
```markdown
🚀 **看涨信号** | Binance
📊 **BTC/USDT**: $45,230.50 ↑ +2.34%

📈 **指标**:
- 成交量: 3.5x 1H均值 (1,250 BTC)
- MA30: $44,100 (上方)
- 1H新高: $45,230.50

⏰ 2026-01-17 14:30:00 UTC
```

**测试场景**:
```python
# TC-F04-01: 成功推送
操作: 触发告警
预期: 飞书收到消息，HTTP 200 响应

# TC-F04-02: Webhook 失败处理
模拟: Webhook URL 返回 500 错误
预期: 日志记录错误，程序继续运行

# TC-F04-03: 网络超时处理
模拟: 请求超时 10 秒
预期: 记录超时日志，不阻塞主流程
```

---

### 2.5 配置管理 (F-05)
**需求描述**: YAML 配置文件管理系统参数

**验收标准**:
- ✅ 配置文件路径: `config.yaml`（可通过环境变量 `SIGNAL_CONFIG` 覆盖）
- ✅ 支持多交易所配置（名称、API 凭证可选）
- ✅ 支持每交易所配置多个市场
- ✅ 支持全局参数配置（MA 周期、成交量倍数、冷却期等）
- ✅ 配置加载失败时程序退出并显示详细错误信息
- ✅ 敏感信息（Webhook URL）支持环境变量替换

**配置文件结构**:
```yaml
# config.yaml
exchanges:
  - name: binance
    markets:
      - BTC/USDT
      - ETH/USDT
    enabled: true

  - name: okx
    markets:
      - BTC/USDT
    enabled: false  # 可禁用单个交易所

indicators:
  ma_period: 30           # MA 周期
  ma_type: SMA            # SMA 或 EMA
  volume_threshold: 3.0   # 成交量倍数
  lookback_bars: 4        # 新高新低回溯根数（1小时）

alerts:
  lark_webhook: "${LARK_WEBHOOK_URL}"  # 环境变量替换
  cooldown_seconds: 300                # 5 分钟冷却期
  rate_limit: 10                       # 每分钟最大推送数

logging:
  level: INFO             # DEBUG, INFO, WARNING, ERROR
  file: logs/signal.log   # 日志文件路径
```

**测试场景**:
```python
# TC-F05-01: 正常加载配置
输入: 有效的 config.yaml
预期: 配置对象正确解析

# TC-F05-02: 配置文件不存在
操作: 删除 config.yaml
预期: 程序退出，错误信息 "Config file not found"

# TC-F05-03: 环境变量替换
设置: export LARK_WEBHOOK_URL="https://..."
预期: 正确替换配置中的 ${LARK_WEBHOOK_URL}

# TC-F05-04: 禁用交易所
配置: okx.enabled = false
预期: 仅订阅 Binance，不连接 OKX
```

---

## 3. 非功能性需求

### 3.1 性能需求 (NFR-01)
- **并发处理**: 支持同时监控 3 个交易所，每个交易所 10 个市场
- **内存占用**: 单市场内存 < 10 MB（100 根 K 线数据）
- **响应延迟**: K 线更新到告警推送 < 2 秒
- **CPU 使用**: 稳定运行时 CPU < 20%（双核机器）

### 3.2 可靠性需求 (NFR-02)
- **故障恢复**: WebSocket 断线自动重连，成功率 > 95%
- **数据准确性**: 技术指标计算错误率 < 0.01%
- **连续运行**: 7x24 小时稳定运行，无内存泄漏

### 3.3 可维护性需求 (NFR-03)
- **代码结构**: 模块化设计，单个文件 < 500 行
- **日志系统**: 分级日志（DEBUG/INFO/WARNING/ERROR）
- **错误处理**: 所有异常捕获并记录，不导致程序崩溃

### 3.4 安全需求 (NFR-04)
- **凭证管理**: Webhook URL 通过环境变量配置，不硬编码
- **API 密钥**: 不在配置文件中存储明文 API 密钥（预留接口）
- **日志脱敏**: 不记录敏感 URL 完整路径

---

## 4. 技术规格

### 4.1 技术栈
| 组件 | 技术选型 | 版本要求 |
|------|---------|---------|
| **语言** | Python | >= 3.10 |
| **包管理** | uv | >= 0.1.0 |
| **交易所 API** | CCXT Pro | >= 4.0.0 |
| **异步框架** | asyncio | 标准库 |
| **数据处理** | pandas | >= 2.0.0 |
| **HTTP 客户端** | httpx | >= 0.25.0 |
| **配置解析** | PyYAML | >= 6.0 |
| **日志** | structlog | >= 23.0.0 |

### 4.2 项目结构
```
signal/
├── pyproject.toml          # uv 项目配置
├── config.yaml             # 用户配置文件
├── config.example.yaml     # 配置文件模板
├── README.md               # 使用文档
├── ACCEPTANCE_CRITERIA.md  # 本文档
├── src/
│   └── signal/
│       ├── __init__.py
│       ├── __main__.py     # 程序入口
│       ├── config.py       # 配置加载模块
│       ├── exchange.py     # 交易所 WebSocket 订阅
│       ├── indicators.py   # 技术指标计算
│       ├── alerts.py       # 告警判断与推送
│       └── utils.py        # 工具函数
├── tests/                  # 单元测试（可选）
│   ├── test_indicators.py
│   └── test_alerts.py
└── logs/                   # 日志输出目录
    └── signal.log
```

### 4.3 外部依赖
- **CCXT Pro**: 需要 Pro 版本（支持 WebSocket）
- **飞书机器人**: 需要提前创建 Webhook URL
- **网络要求**: 稳定的互联网连接，能访问交易所 API

---

## 5. 验收测试计划

### 5.1 单元测试（Unit Test）
| 测试模块 | 覆盖范围 | 预期覆盖率 |
|---------|---------|-----------|
| `indicators.py` | MA30, 成交量异常, 新高新低 | > 90% |
| `alerts.py` | 告警条件判断逻辑 | > 85% |
| `config.py` | 配置加载与验证 | > 80% |

### 5.2 集成测试（Integration Test）
**场景 1: 端到端正常流程**
```
步骤:
1. 启动程序，加载配置
2. 订阅 Binance BTC/USDT
3. 模拟接收满足条件的 K 线数据
4. 验证飞书收到告警消息

预期: 全流程无错误，消息内容正确
```

**场景 2: 异常恢复测试**
```
步骤:
1. 程序正常运行中
2. 断开网络连接 30 秒
3. 恢复网络连接

预期: 自动重连成功，数据流恢复
```

**场景 3: 高负载测试**
```
配置: 3 个交易所，每个 10 个市场（共 30 个市场）
运行: 持续 1 小时
预期: 内存 < 300 MB, CPU < 30%, 无崩溃
```

### 5.3 用户验收测试（UAT）
**UAT-01: 配置部署**
- ✅ 用户能独立完成 uv 环境安装
- ✅ 用户能正确配置 config.yaml
- ✅ 用户能成功启动程序

**UAT-02: 实时监控**
- ✅ 程序运行 24 小时无崩溃
- ✅ 至少捕获 1 次有效告警
- ✅ 飞书消息格式清晰易读

**UAT-03: 问题处理**
- ✅ 网络波动时程序自动恢复
- ✅ 配置错误时有明确提示
- ✅ 日志文件能帮助排查问题

---

## 6. 成功标准

### 6.1 必须达成（Must Have）
- ✅ 功能性需求 F-01 到 F-05 全部实现
- ✅ 所有单元测试通过
- ✅ 端到端集成测试通过
- ✅ 用户验收测试通过

### 6.2 应该达成（Should Have）
- ✅ 代码覆盖率 > 80%
- ✅ 文档完整（README + 配置示例）
- ✅ 性能需求达标（NFR-01）

### 6.3 可以达成（Could Have）
- ⚪ 提供 Docker 镜像
- ⚪ 支持更多交易所（Kraken, Coinbase）
- ⚪ Web 管理界面

---

## 7. 交付物清单

1. ✅ **源代码**: 完整的 Python 项目（uv 管理）
2. ✅ **配置模板**: `config.example.yaml`
3. ✅ **使用文档**: `README.md`（含安装、配置、运行指南）
4. ✅ **验收文档**: 本文档 `ACCEPTANCE_CRITERIA.md`
5. ⚪ **测试报告**: 单元测试和集成测试结果（可选）

---

## 8. 风险与假设

### 8.1 风险
| 风险项 | 影响 | 缓解措施 |
|-------|------|---------|
| CCXT Pro 某些交易所 WebSocket 不稳定 | 数据延迟或丢失 | 实现重连机制，记录异常日志 |
| 飞书 Webhook 限流 | 告警丢失 | 实现本地限流（每分钟 10 条） |
| 内存泄漏 | 长时间运行崩溃 | 限制滑动窗口大小（100 根 K 线） |

### 8.2 假设
- ✅ 用户已有飞书机器人 Webhook URL
- ✅ 用户机器能访问交易所 API（无防火墙限制）
- ✅ Python 3.10+ 环境已安装

---

## 9. 附录

### 9.1 术语表
- **K 线**: 蜡烛图（Candlestick），包含开盘价、收盘价、最高价、最低价、成交量
- **MA30**: 30 周期简单移动平均线
- **WebSocket**: 双向通信协议，用于实时数据推送
- **冷却期**: 防止重复告警的时间间隔

### 9.2 参考资料
- CCXT Pro 文档: https://docs.ccxt.com/#/ccxt.pro.manual
- 飞书机器人文档: https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN
- uv 文档: https://github.com/astral-sh/uv

### 9.3 测试环境配置
**生产环境配置** (用于实际部署和验收测试):

**交易所**: Binance (币安)
**监控市场**:
- BTC/USDT (比特币/USDT)
- ETH/USDT (以太坊/USDT)

**飞书 Webhook URL**:
```
https://open.larksuite.com/open-apis/bot/v2/hook/78a3abef-5c4c-4faa-8342-a537a0820d12
```

**配置文件示例** (config.yaml):
```yaml
exchanges:
  - name: binance
    markets:
      - BTC/USDT
      - ETH/USDT
    enabled: true

indicators:
  ma_period: 30
  ma_type: SMA
  volume_threshold: 3.0
  lookback_bars: 4

alerts:
  lark_webhook: "https://open.larksuite.com/open-apis/bot/v2/hook/78a3abef-5c4c-4faa-8342-a537a0820d12"
  cooldown_seconds: 300
  rate_limit: 10

logging:
  level: INFO
  file: logs/signal.log
```

**环境变量配置** (可选，更安全):
```bash
export LARK_WEBHOOK_URL="https://open.larksuite.com/open-apis/bot/v2/hook/78a3abef-5c4c-4faa-8342-a537a0820d12"
```

**测试检查清单**:
- ✅ Binance WebSocket 连接成功
- ✅ BTC/USDT 和 ETH/USDT 实时数据接收
- ✅ MA30 计算正确（至少需要 7.5 小时积累 30 根 15 分钟 K 线）
- ✅ 成交量异常检测准确
- ✅ 飞书机器人能收到格式化消息
- ✅ 程序持续运行 24 小时无崩溃

---

**文档状态**: ✅ 已批准
**审批人**: Harry
**批准日期**: 2026-01-17
**最后更新**: 2026-01-17 (添加测试环境配置)
