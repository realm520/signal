# Signal - 加密货币行情监控告警系统

实时监控加密货币市场，通过技术指标组合识别交易机会，自动推送告警到飞书。

## 功能特性

✅ **实时 WebSocket 监控**：基于 CCXT Pro 订阅多交易所 15 分钟 K 线数据
✅ **智能告警过滤**：三重条件判断（成交量放大 + MA30 位置 + 价格突破）
✅ **飞书消息推送**：格式化告警消息，包含价格、指标和涨跌幅
✅ **并发多市场**：支持同时监控多个交易所和交易对
✅ **自动重连**：WebSocket 断线自动重连（指数退避策略）
✅ **防重复告警**：5 分钟冷却期 + 每分钟限流机制

## 告警条件

系统在以下条件**同时满足**时触发告警：

### 1. 成交量突然放大
当前 15 分钟成交量 ≥ 前 1 小时平均值的 **3 倍**

### 2. 价格突破（二选一）

**看涨信号** 🚀：
- 价格在 MA30 **上方**
- 突破 1 小时新高

**看跌信号** 📉：
- 价格在 MA30 **下方**
- 突破 1 小时新低

## 快速开始

### 方式一：直接运行（无需克隆仓库）⚡

使用 `uvx` 直接从 GitHub 运行，无需克隆代码：

```bash
# 1. 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 准备配置文件
wget https://raw.githubusercontent.com/realm520/signal/main/config.example.yaml -O config.yaml
# 编辑 config.yaml，填入飞书 Webhook 和监控市场

# 3. 直接运行
uvx git+https://github.com/realm520/signal.git

# 或使用环境变量指定配置路径
SIGNAL_CONFIG=/path/to/config.yaml uvx git+https://github.com/realm520/signal.git
```

**优势**：
- ✅ 零配置，一键运行
- ✅ 自动隔离环境，不污染系统
- ✅ 始终使用最新代码
- ✅ 适合快速体验和测试

### 方式二：本地安装（推荐开发）

#### 前置要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) 包管理器
- 飞书机器人 Webhook URL

#### 安装

1. **克隆或下载项目**
```bash
git clone https://github.com/realm520/signal.git
cd signal
```

2. **安装依赖**
```bash
uv sync
```

#### 配置

**使用交互式向导（推荐新手）**

```bash
python scripts/setup_wizard.py
```

向导会引导你完成:
- ✅ 选择交易所和交易对
- ✅ 配置技术指标参数
- ✅ 设置飞书 Webhook
- ✅ 自动生成 config.yaml

**或手动配置**

1. **创建配置文件**
```bash
cp config.example.yaml config.yaml
```

2. **编辑配置文件**
```yaml
# config.yaml
exchanges:
  - name: binance
    markets:
      - BTC/USDT
      - ETH/USDT
    enabled: true

indicators:
  ma_period: 30           # MA30 周期
  volume_threshold: 3.0   # 3倍成交量

alerts:
  lark_webhook: "https://open.larksuite.com/open-apis/bot/v2/hook/YOUR_WEBHOOK_ID"
  cooldown_seconds: 300   # 5分钟冷却期
```

3. **（可选）使用环境变量**
```bash
export LARK_WEBHOOK_URL="https://open.larksuite.com/..."
```

然后在配置文件中使用：
```yaml
alerts:
  lark_webhook: "${LARK_WEBHOOK_URL}"
```

#### 运行前检查（可选但推荐）

```bash
# 运行系统诊断
python scripts/diagnose.py
```

诊断工具会检查:
- ✅ Python和uv版本
- ✅ 配置文件完整性
- ✅ 依赖包安装状态
- ✅ 网络连接
- ✅ Webhook配置
- ✅ 测试通过情况

#### 运行

```bash
uv run signal
```

或使用 Python 模块方式：
```bash
uv run python -m signal
```

### 停止程序

按 `Ctrl+C` 停止程序。程序会优雅关闭所有 WebSocket 连接。

## 配置说明

### 交易所配置

```yaml
exchanges:
  - name: binance        # 交易所名称（binance, okx, bybit 等）
    markets:
      - BTC/USDT        # 交易对列表
      - ETH/USDT
    enabled: true       # 是否启用（false 则跳过）
```

支持的交易所：
- `binance` - 币安
- `okx` - OKX
- `bybit` - Bybit
- 更多交易所见 [CCXT 文档](https://docs.ccxt.com/#/ccxt.pro.manual)

### 指标配置

```yaml
indicators:
  ma_period: 30           # MA 周期（30 * 15分钟 = 7.5小时）
  ma_type: SMA            # MA 类型：SMA（简单）或 EMA（指数）
  volume_threshold: 3.0   # 成交量倍数阈值
  lookback_bars: 4        # 新高新低回溯周期（4 * 15分钟 = 1小时）
```

### 告警配置

```yaml
alerts:
  lark_webhook: "..."     # 飞书 Webhook URL
  cooldown_seconds: 300   # 同一市场冷却期（秒）
  rate_limit: 10          # 每分钟最大告警数
```

### 日志配置

```yaml
logging:
  level: INFO             # 日志级别：DEBUG, INFO, WARNING, ERROR
  file: logs/signal.log   # 日志文件路径
```

## 告警消息示例

```
🚀 **看涨信号** | Binance
📊 **BTC/USDT**: $45,230.50 ↑ +2.34%

📈 **指标**:
- 成交量: 3.5x 1H均值 (1,250.00)
- MA30: $44,100.00 (上方)
- 1H参考价: $44,200.00

⏰ 2026-01-17 14:30:00 UTC
```

## 策略回测

项目提供完整的回测工具链，支持获取真实历史数据并评估策略有效性。

### 获取真实历史数据

使用 `fetch_historical_data.py` 从交易所下载历史K线数据:

```bash
# 获取Binance的BTC/USDT 30天数据
python scripts/fetch_historical_data.py \
  --symbol BTC/USDT \
  --days 30

# 使用其他交易所 (推荐使用OKX或Bybit避免限流)
python scripts/fetch_historical_data.py \
  --exchange okx \
  --symbol BTC/USDT \
  --days 30 \
  --output data/okx_btc_30d.json

# 查看帮助
python scripts/fetch_historical_data.py --help
```

**数据文件格式**:
```json
[
  {
    "timestamp": 1736812800,
    "open": 102500.0,
    "high": 102800.0,
    "low": 102200.0,
    "close": 102650.0,
    "volume": 1250.5
  },
  ...
]
```

### 运行回测

使用 `backtest_simple.py` 进行策略回测:

```bash
# 使用真实数据回测
python scripts/backtest_simple.py \
  --data data/binance_BTC_USDT_30d.json \
  --ma-period 30 \
  --volume-threshold 3.0

# 使用模拟数据快速测试
python scripts/backtest_simple.py --days 30

# 查看帮助
python scripts/backtest_simple.py --help
```

**回测输出示例**:

```
📊 回测结果
======================================================================

📈 告警统计:
   总告警数: 26
   看涨告警: 13 (50.0%)
   看跌告警: 13 (50.0%)

⏱️  时间分析:
   平均告警间隔: 363.0 分钟
   最短间隔: 75.0 分钟
   最长间隔: 675.0 分钟

🔔 最近5个告警:
   🚀 2026-01-17 18:19 | bullish  | $43657.14 | MA:42819.08 | Vol:5.0x
   📉 2026-01-17 19:34 | bearish  | $42079.46 | MA:42814.73 | Vol:4.8x
```

**注意事项**:
- 推荐使用真实历史数据进行回测以获得准确评估
- 某些交易所可能有API限流，推荐使用OKX或Bybit
- 回测结果不代表未来表现，仅供参考
- 建议先通过纸上交易验证策略有效性

**完整回测工作流**:
```bash
# 1. 获取30天真实数据
python scripts/fetch_historical_data.py --exchange okx --symbol BTC/USDT --days 30

# 2. 运行回测
python scripts/backtest_simple.py --data data/okx_BTC_USDT_30d.json

# 3. 分析结果，调整参数后重新测试
python scripts/backtest_simple.py \
  --data data/okx_BTC_USDT_30d.json \
  --ma-period 20 \
  --volume-threshold 2.5
```

## 项目结构

```
signal/
├── pyproject.toml              # uv 项目配置
├── config.yaml                 # 用户配置文件
├── config.example.yaml         # 配置模板
├── README.md                   # 本文件
├── ACCEPTANCE_CRITERIA.md      # 验收规格文档
├── src/signal/
│   ├── __init__.py
│   ├── __main__.py            # 程序入口
│   ├── config.py              # 配置加载
│   ├── exchange.py            # WebSocket 订阅
│   ├── indicators.py          # 技术指标计算
│   ├── alerts.py              # 告警判断和推送
│   └── utils.py               # 工具函数
└── logs/
    └── signal.log             # 日志文件
```

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.10+ | 现代 Python 特性 |
| 包管理 | uv | 快速依赖管理 |
| 交易所 API | CCXT Pro | WebSocket 实时数据 |
| 异步框架 | asyncio | 并发处理 |
| 数据处理 | pandas | 技术指标计算 |
| HTTP 客户端 | httpx | 异步 HTTP 请求 |
| 配置解析 | PyYAML | YAML 配置文件 |
| 日志 | structlog | 结构化日志 |

## 常见问题

### Q: 程序启动后多久才会开始告警？

**A**: 需要等待至少 7.5 小时（30 根 15 分钟 K 线）才能计算 MA30。在此之前，程序会接收数据但不会触发告警。

### Q: 如何测试飞书 Webhook 是否正常？

**A**: 使用 `curl` 命令测试：
```bash
curl -X POST "YOUR_WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{"msg_type":"text","content":{"text":"测试消息"}}'
```

### Q: 程序占用内存会不断增长吗？

**A**: 不会。每个市场最多保留 100 根 K 线数据（约 6.25 MB），使用滑动窗口自动清理旧数据。

### Q: 支持现货和合约市场吗？

**A**: 是的。只要交易所提供 WebSocket 接口，都可以监控。交易对格式参考 CCXT 文档。

### Q: 如何禁用某个交易所？

**A**: 在配置文件中设置 `enabled: false`：
```yaml
exchanges:
  - name: okx
    enabled: false  # 不监控 OKX
```

### Q: 日志文件在哪里？

**A**: 默认在 `logs/signal.log`。可在配置文件中修改路径。

## 故障排查

### 配置文件错误
```
FileNotFoundError: Config file not found
```
**解决**：确保 `config.yaml` 存在，或设置 `SIGNAL_CONFIG` 环境变量。

### Webhook 推送失败
```
alert_send_failed: HTTPError
```
**解决**：
1. 检查 Webhook URL 是否正确
2. 确认飞书机器人未被停用
3. 检查网络连接

### WebSocket 连接失败
```
connection_error: exchange=binance
```
**解决**：
1. 检查网络连接
2. 确认交易所 API 可访问
3. 查看日志详细错误信息

### 数据不足无法计算
```
insufficient_data: current=10, required=30
```
**解决**：这是正常现象，等待足够的 K 线数据积累（约 7.5 小时）。

## 性能指标

- **内存占用**：< 10 MB / 市场（100 根 K 线）
- **CPU 使用**：< 20%（稳定运行时）
- **响应延迟**：K 线更新到告警推送 < 2 秒
- **并发能力**：支持 3 个交易所 × 10 个市场

## 安全建议

1. **不要提交配置文件**：`config.yaml` 包含 Webhook URL，建议加入 `.gitignore`
2. **使用环境变量**：生产环境建议用环境变量存储敏感信息
3. **定期更新依赖**：运行 `uv sync` 更新到最新安全版本

## 开发

### 安装开发依赖
```bash
uv sync --all-extras
```

### 运行测试
```bash
uv run pytest
```

### 配置验证
```bash
# 验证配置文件
python scripts/validate_config.py

# 验证指定文件
python scripts/validate_config.py --config /path/to/config.yaml
```

### 性能基准测试
```bash
# 默认测试 (10,000 bars)
python scripts/benchmark.py

# 自定义参数
python scripts/benchmark.py --bars 100000 --iterations 20
```

### 代码格式化
```bash
uv run ruff check src/
uv run ruff format src/
```

## 生产部署

### 方式一: Systemd 服务 (Linux 推荐)

适用于 Linux 服务器,使用 systemd 管理进程:

```bash
# 1. 自动部署 (推荐)
sudo ./scripts/deploy_systemd.sh

# 2. 编辑配置
sudo nano /opt/signal/config.yaml

# 3. 重启服务
sudo systemctl restart signal

# 4. 查看日志
sudo journalctl -u signal -f
```

**服务管理命令**:
```bash
sudo systemctl start signal      # 启动
sudo systemctl stop signal       # 停止
sudo systemctl restart signal    # 重启
sudo systemctl status signal     # 状态
```

**健康检查**:
```bash
# 运行健康检查脚本
python scripts/health_check.py
```

### 方式二: Docker 部署

#### 使用 Docker Compose (推荐)

1. **构建镜像**
```bash
docker-compose build
```

2. **准备配置文件**
```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml 设置 Webhook URL 和监控市场
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **查看日志**
```bash
docker-compose logs -f signal
```

5. **停止服务**
```bash
docker-compose down
```

### 方式三: 手动运行 (开发/测试)

```bash
# 直接运行
uv run signal

# 或使用 Python 模块
uv run python -m signal_app
```

## 运维管理

### 日志管理

**Systemd 部署**:
```bash
# 查看实时日志
sudo journalctl -u signal -f

# 查看最近100条
sudo journalctl -u signal -n 100

# 查看今天的日志
sudo journalctl -u signal --since today
```

**Docker 部署**:
```bash
# 查看实时日志
docker-compose logs -f signal

# 查看最近100条
docker-compose logs --tail=100 signal
```

**文件日志** (所有部署方式):
```bash
# 日志位置
tail -f logs/signal.log

# 按日期归档 (可添加到cron)
gzip logs/signal.log.$(date +%Y%m%d)
```

### 性能监控

**基础监控**:
```bash
# 系统资源监控 (systemd)
systemctl status signal

# Docker资源监控
docker stats signal-monitor

# 健康检查
python scripts/health_check.py
```

**告警统计分析**:
```bash
# 分析最近7天的告警
python scripts/alert_stats.py

# 分析最近30天
python scripts/alert_stats.py --days 30

# 指定日志文件
python scripts/alert_stats.py --log /path/to/signal.log
```

**Prometheus + Grafana 完整监控栈**:

1. **启动 Signal Prometheus Exporter**:
```bash
# 方式1: 直接运行
python scripts/prometheus_exporter.py --port 9090

# 方式2: Systemd服务
sudo cp scripts/signal-exporter.service /etc/systemd/system/
sudo systemctl enable signal-exporter
sudo systemctl start signal-exporter

# 方式3: Docker
docker run -d --name signal-exporter \
  -p 9090:9090 \
  -v $(pwd)/logs:/app/logs:ro \
  signal:latest python scripts/prometheus_exporter.py
```

2. **配置 Prometheus**:
```bash
# 添加Signal job到Prometheus配置
# 参考: scripts/prometheus.yml

# 添加告警规则
# 参考: scripts/signal_alerts.yml
```

3. **导入 Grafana Dashboard**:
```bash
# 导入预配置的dashboard
# 文件: scripts/grafana-dashboard.json
# Grafana UI: Dashboards → Import → Upload JSON file
```

**暴露的指标**:
- `signal_alerts_total{type="bullish|bearish"}` - 24小时内告警总数
- `signal_health_status{component="log|config"}` - 组件健康状态 (1=健康, 0=异常)
- `signal_log_age_seconds` - 日志文件最后更新距今秒数

**预配置的告警规则**:
- `SignalLogStale` - 日志5分钟未更新
- `SignalLogUnhealthy` - 日志组件异常
- `SignalConfigMissing` - 配置文件缺失
- `SignalNoAlertsLongTime` - 24小时无告警(可能市场平静或检测失败)
- `SignalHighAlertRate` - 告警频率异常高(可能误报)

### 配置热更新

修改配置后重启服务:

```bash
# Systemd
sudo systemctl restart signal

# Docker Compose
docker-compose restart signal

# 手动运行 (Ctrl+C 然后重新运行)
```

## 许可证

MIT License

## 文档

### 项目文档
- 📖 [README.md](README.md) - 本文件，快速开始指南
- 🤖 [CLAUDE.md](CLAUDE.md) - Claude Code 集成指南

### 外部文档
- [CCXT Pro 文档](https://docs.ccxt.com/#/ccxt.pro.manual) - WebSocket API 参考
- [飞书机器人文档](https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN) - Webhook 集成

## 支持

遇到问题？

1. 查看 [CLAUDE.md](CLAUDE.md) 了解完整的架构和配置说明
2. 运行 `python scripts/diagnose.py` 进行系统诊断
3. 搜索或创建 [GitHub Issue](https://github.com/realm520/signal/issues)

## 贡献

欢迎贡献！提交 Pull Request 前请确保：
- ✅ 代码通过 `uv run ruff check` 检查
- ✅ 测试通过 `uv run pytest`
- ✅ 遵循现有代码风格和架构模式

## 许可证

MIT License

---

**祝交易顺利！** 🚀
