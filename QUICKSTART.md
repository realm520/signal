# Signal 快速启动指南

5 分钟快速部署加密货币监控系统。

## 前置要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) 包管理器
- 飞书机器人 Webhook URL

## 快速开始

### 1. 安装依赖（30 秒）

```bash
cd signal
uv sync
```

### 2. 启动程序（立即）

```bash
# 使用现有配置（已配置 Binance BTC/ETH + 飞书 Webhook）
uv run signal
```

程序将立即开始监控：
- 交易所: Binance (币安)
- 市场: BTC/USDT, ETH/USDT
- K线: 15 分钟
- 指标: MA30, 成交量 3x, 1H 新高新低

### 3. 查看日志

```bash
# 实时查看日志
tail -f logs/signal.log
```

### 4. 停止程序

```
Ctrl + C
```

---

## 预期行为

### 启动阶段（前 7.5 小时）
```
✅ 连接 Binance WebSocket
✅ 接收 BTC/USDT 和 ETH/USDT 数据
⏳ 积累 K 线数据（至少 30 根）
⚪ 暂不触发告警（数据不足）
```

### 稳定运行阶段（7.5 小时后）
```
✅ MA30 计算正常
✅ 实时监控成交量和价格突破
🔔 满足条件时推送飞书告警
```

---

## 告警条件

系统在以下条件**全部满足**时推送告警：

1. ✅ 成交量放大（当前 >= 前 1 小时均值 * 3 倍）
2. ✅ 看涨: 价格在 MA30 上方 **且** 突破 1 小时新高
   **或**
   看跌: 价格在 MA30 下方 **且** 突破 1 小时新低

---

## 飞书告警示例

<img width="400" alt="告警消息示例" src="https://via.placeholder.com/400x300/4A90E2/FFFFFF?text=Lark+Alert">

```
🚀 **看涨信号** | Binance
📊 **BTC/USDT**: $45,230.50 ↑ +2.34%

📈 **指标**:
- 成交量: 3.5x 1H均值 (1,250.00)
- MA30: $44,100.00 (上方)
- 1H参考价: $44,200.00

⏰ 2026-01-17 14:30:00 UTC
```

---

## 自定义配置（可选）

编辑 `config.yaml` 修改配置：

```yaml
# 修改监控市场
exchanges:
  - name: binance
    markets:
      - BTC/USDT
      - ETH/USDT
      - SOL/USDT  # 添加更多市场

# 调整指标参数
indicators:
  ma_period: 30           # MA 周期
  volume_threshold: 3.0   # 成交量倍数（3x）

# 修改告警设置
alerts:
  cooldown_seconds: 300   # 冷却期（5 分钟）
  rate_limit: 10          # 每分钟最大告警数
```

---

## 故障排查

### 问题 1: "Config file not found"
```bash
# 确保 config.yaml 存在
ls config.yaml

# 或使用示例配置
cp config.example.yaml config.yaml
```

### 问题 2: "No module named 'signal_app'"
```bash
# 重新安装依赖
uv sync
```

### 问题 3: Webhook 推送失败
```bash
# 测试 Webhook 连接
uv run python tests/test_webhook.py
```

### 问题 4: 程序启动后无输出
```bash
# 这是正常的！程序在后台监控
# 查看日志确认运行状态
tail -f logs/signal.log

# 应该看到类似输出：
# {"event": "watching_market", "exchange": "binance", "market": "BTC/USDT"}
```

---

## 下一步

- 📖 查看 [README.md](README.md) 了解完整文档
- 📋 查看 [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md) 了解功能规格
- ✅ 查看 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) 了解实现状态

---

**提示**: 程序需要至少 7.5 小时（30 根 15 分钟 K 线）才能计算 MA30 并开始告警。在此之前，它会安静地收集数据。这是正常行为！

**祝交易顺利！** 🚀
