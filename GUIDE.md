# Signal 项目完整指南

**版本**: v0.1.0
**更新时间**: 2026-01-18
**Ralph Loop**: Iteration 22

---

## 📋 目录

1. [项目概述](#项目概述)
2. [快速开始](#快速开始)
3. [配置指南](#配置指南)
4. [部署方式](#部署方式)
5. [运维监控](#运维监控)
6. [策略回测](#策略回测)
7. [故障排查](#故障排查)
8. [项目状态](#项目状态)

---

## 项目概述

Signal 是一个实时加密货币市场监控和告警系统，基于技术指标自动检测市场异常并通过飞书推送通知。

### 核心特性

- ✅ **实时监控**: WebSocket 订阅多交易所K线数据
- ✅ **技术指标**: MA30移动平均、成交量异常、价格突破
- ✅ **智能告警**: 复合条件判断 + 冷却期机制
- ✅ **飞书推送**: Markdown格式化消息，限流保护
- ✅ **完整测试**: 41个测试用例，100%通过
- ✅ **生产就绪**: Docker/Systemd部署，Prometheus监控
- ✅ **策略回测**: 模拟数据 + 真实历史数据支持

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | 异步编程 |
| 包管理 | uv | 快速依赖管理 |
| 数据源 | CCXT Pro | WebSocket实时数据 |
| 通知 | 飞书Webhook | 消息推送 |
| 测试 | pytest | 单元测试 + 集成测试 |
| 监控 | Prometheus/Grafana | 指标采集和可视化 |
| 部署 | Docker/Systemd | 容器化 + 系统服务 |

---

## 快速开始

### 1. 环境要求

- Python 3.11+
- uv 包管理器
- 飞书机器人 Webhook URL

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd signal

# 安装依赖
uv sync
```

### 3. 配置文件

**方式一**: 使用配置向导（推荐新手）

```bash
python scripts/setup_wizard.py
```

**方式二**: 手动配置

```bash
# 复制配置模板
cp config.example.yaml config.yaml

# 编辑配置
vim config.yaml
```

最小配置示例:

```yaml
exchanges:
  - name: binance
    markets: ["BTC/USDT", "ETH/USDT"]
    enabled: true

indicators:
  ma_period: 30
  ma_type: SMA
  volume_threshold: 3.0
  lookback_bars: 4

alerts:
  lark_webhook: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK"
  cooldown_seconds: 300
  rate_limit: 10

logging:
  level: INFO
  file: logs/signal.log
```

### 4. 运行程序

```bash
# 创建日志目录
mkdir -p logs

# 运行
uv run signal
```

### 5. 验证系统

```bash
# 系统诊断（检查配置、依赖、网络等）
python scripts/diagnose.py

# 配置验证
python scripts/validate_config.py

# 运行测试
uv run pytest tests/ -v
```

---

## 配置指南

### 交易所配置

支持所有CCXT兼容的交易所:

```yaml
exchanges:
  - name: binance      # 交易所名称
    markets:           # 监控的交易对列表
      - BTC/USDT
      - ETH/USDT
      - SOL/USDT
    enabled: true      # 是否启用

  - name: okx
    markets:
      - BTC/USDT
    enabled: true
```

### 指标配置

```yaml
indicators:
  ma_period: 30              # MA周期 (30 * 15分钟 = 7.5小时)
  ma_type: SMA               # SMA(简单) 或 EMA(指数)
  volume_threshold: 3.0      # 成交量倍数阈值
  lookback_bars: 4           # 新高新低回溯周期
```

**告警触发条件** (需同时满足):
1. 成交量 > 近3根K线平均值 × 3.0倍
2. 价格相对MA30位置 (上方看涨/下方看跌)
3. 创造新高或新低 (相对前3根K线)

### 告警配置

```yaml
alerts:
  lark_webhook: "..."        # 飞书Webhook URL (必填)
  cooldown_seconds: 300      # 同一市场冷却期 (秒)
  rate_limit: 10             # 每分钟最大告警数
```

### 日志配置

```yaml
logging:
  level: INFO                # DEBUG/INFO/WARNING/ERROR
  file: logs/signal.log      # 日志文件路径
```

---

## 部署方式

### 方式一: Docker (推荐)

```bash
# 构建镜像
docker build -t signal:latest .

# 或使用 docker-compose
docker-compose up -d

# 查看日志
docker-compose logs -f signal
```

### 方式二: Systemd 系统服务

```bash
# 自动部署
sudo bash scripts/deploy_systemd.sh

# 手动管理
sudo systemctl start signal
sudo systemctl status signal
sudo systemctl enable signal  # 开机自启
```

### 方式三: 手动运行

```bash
# 前台运行
uv run signal

# 后台运行
nohup uv run signal > logs/signal.log 2>&1 &

# 查看进程
ps aux | grep signal
```

---

## 运维监控

### 健康检查

```bash
# 快速健康检查
python scripts/health_check.py

# 系统诊断（更全面）
python scripts/diagnose.py
```

### 日志分析

```bash
# 告警统计
python scripts/alert_stats.py

# 查看最近日志
tail -f logs/signal.log

# 查看错误日志
grep ERROR logs/signal.log
```

### Prometheus 监控

```bash
# 启动指标导出器
python scripts/prometheus_exporter.py &

# 访问指标
curl http://localhost:9090/metrics
```

**可用指标**:
- `signal_alerts_total{type="bullish|bearish"}` - 告警总数
- `signal_health_status{component="..."}` - 组件健康状态
- `signal_log_age_seconds` - 日志更新时间

### Grafana 仪表盘

```bash
# 导入仪表盘
# 在Grafana中导入 scripts/grafana-dashboard.json
```

**包含面板**:
- 告警速率趋势图
- 告警类型分布
- 系统健康状态
- 日志活跃度

---

## 策略回测

### 获取真实历史数据

```bash
# 从OKX获取30天BTC数据（推荐，避免限流）
python scripts/fetch_historical_data.py \
  --exchange okx \
  --symbol BTC/USDT \
  --days 30 \
  --output data/okx_btc_30d.json

# 其他交易所
python scripts/fetch_historical_data.py --exchange bybit --symbol ETH/USDT --days 7
```

### 运行回测

```bash
# 使用真实数据
python scripts/backtest_simple.py \
  --data data/okx_btc_30d.json \
  --ma-period 30 \
  --volume-threshold 3.0

# 使用模拟数据（快速测试）
python scripts/backtest_simple.py --days 30
```

### 回测输出解读

```
📈 告警统计:
   总告警数: 26              # 30天内触发26次告警
   看涨告警: 13 (50.0%)      # 看涨13次
   看跌告警: 13 (50.0%)      # 看跌13次

⏱️  时间分析:
   平均告警间隔: 363.0 分钟  # 约6小时一次
   最短间隔: 75.0 分钟       # 最密集时1.25小时
   最长间隔: 675.0 分钟      # 最长11.25小时
```

### 参数优化工作流

```bash
# 1. 获取数据
python scripts/fetch_historical_data.py --exchange okx --symbol BTC/USDT --days 30

# 2. 基准测试
python scripts/backtest_simple.py --data data/okx_BTC_USDT_30d.json

# 3. 调整MA周期
python scripts/backtest_simple.py --data data/okx_BTC_USDT_30d.json --ma-period 20
python scripts/backtest_simple.py --data data/okx_BTC_USDT_30d.json --ma-period 40

# 4. 调整成交量阈值
python scripts/backtest_simple.py --data data/okx_BTC_USDT_30d.json --volume-threshold 2.5
python scripts/backtest_simple.py --data data/okx_BTC_USDT_30d.json --volume-threshold 4.0

# 5. 选择最优参数部署
```

---

## 故障排查

### 常见问题

**Q1: 程序启动后一直没有告警？**

A: 正常现象。需要满足以下条件:
- 至少收集30根K线（7.5小时）才能计算MA30
- 市场需要出现符合条件的突破（成交量激增 + 价格突破 + 新高/新低）
- 检查日志确认数据正在接收: `tail -f logs/signal.log`

**Q2: 遇到"WebSocket connection failed"错误？**

A: 检查以下几点:
```bash
# 1. 网络连接
ping api.binance.com

# 2. 防火墙设置
# 确保允许WebSocket连接

# 3. 尝试其他交易所
# 在config.yaml中更换为okx或bybit
```

**Q3: 飞书消息没有收到？**

A: 验证Webhook:
```bash
# 测试Webhook
python scripts/test_lark.py

# 或使用curl
curl -X POST "YOUR_WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{"msg_type":"text","content":{"text":"测试"}}'
```

**Q4: 程序占用内存不断增长？**

A: 不会。程序使用滑动窗口，每个市场最多保留100根K线（约6.25MB）。
检查: `ps aux | grep signal`

**Q5: Docker容器无法启动？**

A: 检查配置:
```bash
# 查看容器日志
docker-compose logs signal

# 常见原因:
# - config.yaml未配置
# - Webhook URL无效
# - 端口冲突
```

### 系统诊断工具

```bash
# 运行全面诊断
python scripts/diagnose.py

# 检查项目:
# ✅ Python版本
# ✅ uv安装
# ✅ 配置文件
# ✅ 依赖包
# ✅ 日志目录
# ✅ 网络连接
# ✅ Webhook配置
# ✅ 测试套件
```

### 日志级别调整

编辑 `config.yaml`:

```yaml
logging:
  level: DEBUG  # 获取更详细的日志
```

重启程序后查看详细日志:

```bash
tail -f logs/signal.log | grep DEBUG
```

---

## 项目状态

### 验收标准

**ACCEPTANCE_CRITERIA.md**: 57/57 ✅ (100%)

所有功能需求、非功能需求和UAT测试已完成并验证。

### 测试覆盖

**测试套件**: 41/41 ✅ (100%)

```bash
# 运行所有测试
uv run pytest tests/ -v

# 测试分布:
# - 单元测试: 40个 (indicators, alerts, config, exchange, lark)
# - 集成测试: 1个 (完整流程验证)
# - UAT验证: 加速24小时测试
```

### 代码统计

- **核心代码**: 1,147行 (src/)
- **测试代码**: 1,689行 (tests/)
- **运维工具**: 2,393行 (scripts/)
- **总计**: 5,229行

### Ralph Loop 进展

**迭代次数**: 22
**模式**: 无限迭代持续改进

**已完成改进** (Iteration 20-22):
1. 项目结构重组
2. Docker容器化
3. Systemd生产部署
4. Prometheus监控集成
5. Grafana可视化
6. 配置验证 + 性能基准
7. 项目治理文档
8. 交互式配置向导
9. 系统诊断工具
10. 策略回测工具
11. 真实历史数据支持
12. 项目文档整合 (当前)

### 生产就绪性

- ✅ 核心功能100%完成
- ✅ 测试覆盖100%通过
- ✅ 3种部署方式
- ✅ 完整监控方案
- ✅ 运维工具齐全
- ✅ 文档完整清晰
- ✅ 回测工具完备

**状态**: ✅ 可用于生产环境部署

---

## 获取帮助

### 文档资源

- **README.md**: 项目概览和基础使用
- **GUIDE.md**: 本文档，完整指南
- **ACCEPTANCE_CRITERIA.md**: 功能规格说明
- **CHANGELOG.md**: 版本历史
- **CONTRIBUTING.md**: 贡献指南
- **SECURITY.md**: 安全最佳实践

### 工具命令

```bash
# 配置向导
python scripts/setup_wizard.py

# 系统诊断
python scripts/diagnose.py

# 健康检查
python scripts/health_check.py

# 配置验证
python scripts/validate_config.py

# 性能测试
python scripts/benchmark.py

# 告警统计
python scripts/alert_stats.py

# 回测工具
python scripts/backtest_simple.py --help

# 数据获取
python scripts/fetch_historical_data.py --help
```

---

**项目版本**: v0.1.0
**最后更新**: 2026-01-18
**Ralph Loop**: Iteration 22
**状态**: ✅ 生产就绪
