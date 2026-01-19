# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Signal 是一个实时加密货币市场监控和告警系统，基于技术指标组合（MA30 + 成交量突破 + 价格新高/新低）自动检测交易机会并通过飞书推送告警。

## 核心架构

### 主要模块

```
src/signal_app/
├── __main__.py      # 程序入口，协调所有模块
├── config.py        # 配置加载（YAML + 环境变量）
├── exchange.py      # WebSocket 订阅和 K 线数据接收
├── indicators.py    # 技术指标计算（MA、成交量、新高新低）
├── alerts.py        # 告警判断和飞书消息推送
└── utils.py         # 工具函数（日志、时间格式化等）
```

### 数据流

```
WebSocket K线数据 → ExchangeMonitor → IndicatorEngine → AlertManager → 飞书
                     (exchange.py)    (indicators.py)   (alerts.py)
```

**关键流程**:
1. `ExchangeMonitor` 订阅交易所 WebSocket，接收 15 分钟 K 线数据
2. `IndicatorEngine` 维护滑动窗口（最多 100 根 K 线），计算 MA30 和成交量指标
3. `AlertManager` 判断三重条件（成交量放大 + MA30 位置 + 价格突破），满足则推送告警
4. 冷却期机制：同一市场 5 分钟内不重复告警，全局每分钟最多 10 条

### 告警触发条件

**必须同时满足**以下三个条件:

1. **成交量突破**: 当前成交量 ≥ 前 3 根 K 线平均值 × 3.0 倍
2. **MA30 位置**:
   - 看涨：价格在 MA30 上方
   - 看跌：价格在 MA30 下方
3. **价格突破**:
   - 看涨：创 1 小时新高（相对前 4 根 K 线）
   - 看跌：创 1 小时新低（相对前 4 根 K 线）

## 开发命令

### 依赖管理
```bash
uv sync              # 安装依赖
uv sync --all-extras # 安装开发依赖
```

### 运行程序
```bash
uv run signal                  # 主程序
uv run python -m signal_app    # 或使用模块方式
```

### 测试
```bash
uv run pytest                  # 运行所有测试
uv run pytest tests/test_indicators.py -v  # 运行特定测试
uv run pytest -k "test_ma"     # 运行匹配的测试
```

### 代码质量
```bash
uv run ruff check src/         # 检查代码风格
uv run ruff format src/        # 自动格式化
```

### 运维工具
```bash
python scripts/diagnose.py              # 系统诊断（检查配置、依赖、网络）
python scripts/validate_config.py      # 验证配置文件
python scripts/setup_wizard.py         # 交互式配置向导
python scripts/benchmark.py            # 性能基准测试
python scripts/alert_stats.py          # 告警统计分析
python scripts/health_check.py         # 健康检查
```

### 回测工具
```bash
# 获取真实历史数据（推荐用 OKX 避免限流）
python scripts/fetch_historical_data.py \
  --exchange okx \
  --symbol BTC/USDT \
  --days 30

# 运行回测
python scripts/backtest_simple.py \
  --data data/okx_BTC_USDT_30d.json \
  --ma-period 30 \
  --volume-threshold 3.0
```

## 配置文件

### 主配置: config.yaml

基于 `config.example.yaml` 创建。必需字段:

- `exchanges`: 交易所列表，每个包含 `name`, `markets`, `enabled`
- `indicators`: `ma_period`, `ma_type`, `volume_threshold`, `lookback_bars`
- `alerts`: `lark_webhook`（飞书 Webhook URL）
- `logging`: `level`, `file`

**可选字段**:
- `alerts.mention_user_id`: 在告警消息中 @ 用户（两种方式）
  - **方式 1（推荐）**: 直接填写飞书显示名称，如 `"ZhangHarry"`（简单文本显示，无通知）
  - **方式 2**: 使用 open_id，如 `"ou_xxxxx"`（真正的 @ 通知，需要获取 open_id）
  - 详见 `docs/飞书@功能使用说明.md`

**环境变量替换**: 配置中可用 `${ENV_VAR}` 引用环境变量，如 `lark_webhook: "${LARK_WEBHOOK_URL}"`

**@ 功能配置示例**:
```yaml
alerts:
  lark_webhook: "https://open.larksuite.com/..."
  mention_user_id: "ZhangHarry"  # 方式 1: 简单文本（推荐）
  # mention_user_id: "ou_xxxxxx"  # 方式 2: 真正的通知（需要 open_id）
```

## 开发规范

### Git 分支
- `main`: 稳定生产代码
- `feature/*`: 新功能开发
- `fix/*`: Bug 修复

### 代码风格
- 遵循 PEP 8，使用 ruff 检查和格式化
- 所有函数添加类型提示和 Google 风格 docstrings
- 测试文件命名: `test_*.py`，测试类: `Test*`

### 提交规范
```
类型: 简短描述

详细说明（可选）

相关 Issue: #123
```
类型: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

## 部署方式

### Docker
```bash
docker-compose up -d         # 启动
docker-compose logs -f signal # 查看日志
```

### Systemd（Linux）
```bash
sudo bash scripts/deploy_systemd.sh  # 自动部署
sudo systemctl start signal          # 启动服务
```

### 手动运行
```bash
uv run signal                        # 前台运行
nohup uv run signal > logs/signal.log 2>&1 &  # 后台运行
```

## 监控

### Prometheus + Grafana
```bash
# 启动 Prometheus exporter
python scripts/prometheus_exporter.py --port 9090

# 导入 Grafana dashboard
# 文件: scripts/grafana-dashboard.json
```

**暴露的指标**:
- `signal_alerts_total{type="bullish|bearish"}` - 24 小时告警总数
- `signal_health_status{component="log|config"}` - 组件健康状态
- `signal_log_age_seconds` - 日志最后更新距今秒数

## 注意事项

### 数据冷启动
程序启动后需要至少 30 根 15 分钟 K 线（约 7.5 小时）才能计算 MA30 并开始告警判断。

### 内存管理
每个市场维护滑动窗口，最多保留 100 根 K 线（约 6.25 MB），旧数据自动清理。

### 告警去重
- 同一市场 5 分钟冷却期（`cooldown_seconds: 300`）
- 全局每分钟最多 10 条告警（`rate_limit: 10`）

### 配置验证
修改配置后建议运行 `python scripts/validate_config.py` 验证语法和完整性。

## 文档资源

- **README.md**: 快速开始和基础使用
- **GUIDE.md**: 完整操作指南
- **ACCEPTANCE_CRITERIA.md**: 功能规格和验收标准
- **CONTRIBUTING.md**: 贡献指南和开发规范
- **SECURITY.md**: 安全最佳实践
