# Changelog

所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.1.0] - 2026-01-18

### 核心功能

#### Added - 新增
- **数据订阅层**: WebSocket 实时接收 15 分钟 K 线数据
  - 支持多交易所并行订阅 (Binance, OKX, Bybit)
  - 自动重连机制(最大5次,指数退避)
  - asyncio 并发处理

- **技术指标计算引擎**:
  - MA30 (Simple Moving Average)
  - 成交量异常检测(3倍阈值)
  - 1小时新高新低判断
  - 滑动窗口内存优化(maxlen=100)

- **告警判断引擎**:
  - 三重条件判断(成交量 + MA位置 + 价格突破)
  - 看涨/看跌信号识别
  - 5分钟冷却期
  - 消息限流(10条/分钟)

- **飞书消息推送**:
  - Markdown 格式化消息
  - 包含价格、指标、涨跌幅
  - 错误处理和重试

- **配置管理**:
  - YAML 配置文件
  - 环境变量替换
  - 多交易所/市场配置
  - 参数验证

### 部署与运维

#### Added - 新增
- **Docker 支持**:
  - Dockerfile 基于 Python 3.11-slim
  - docker-compose.yml 配置
  - 配置热挂载和日志持久化
  - 资源限制(CPU 1核, 内存512M)

- **Systemd 服务**:
  - signal.service 配置
  - 自动部署脚本(deploy_systemd.sh)
  - 安全加固(NoNewPrivileges, ProtectSystem)
  - 自动重启策略

- **运维工具集**:
  - `health_check.py` - 健康检查
  - `alert_stats.py` - 告警统计分析
  - `validate_config.py` - 配置验证
  - `benchmark.py` - 性能基准测试

### 监控与可观测性

#### Added - 新增
- **Prometheus 集成**:
  - prometheus_exporter.py (HTTP metrics endpoint)
  - 3个核心指标暴露
  - signal-exporter.service (独立服务)

- **Grafana Dashboard**:
  - 预配置的 JSON dashboard
  - 4个可视化 panel
  - 30秒自动刷新

- **告警规则**:
  - 5个 Prometheus 告警规则
  - 分级严重性(info/warning/critical)
  - 日志停滞、配置缺失、异常频率检测

### 测试

#### Added - 新增
- 41个自动化测试:
  - 40个单元测试
  - 1个集成测试
  - 1个 UAT 验证测试
- 100% 测试通过率
- UAT-02 加速测试(96根K线模拟24小时)

### 文档

#### Added - 新增
- README.md (360+行完整文档)
- ACCEPTANCE_CRITERIA.md (验收规格)
- SECURITY.md (安全最佳实践)
- CONTRIBUTING.md (贡献指南)
- 19个验收报告文档(claudedocs/)

### 性能

- **指标计算**: 344K calculations/sec (2.90μs/calc)
- **K线处理**: 26M bars/sec (0.04μs/bar)
- **内存效率**: O(1) 滑动窗口
- **资源占用**: ~200 bytes/bar

### Fixed - 修复
- 修复指标计算切片逻辑错误(Commit d2e5222)
  - 成交量/新高/新低检测从4根K线改为正确的3根K线
  - 符合 ACCEPTANCE_CRITERIA.md:68 行公式规范

- 修复 async 测试标记缺失(Commit a5ce043)
  - 添加 @pytest.mark.asyncio 装饰器

### Changed - 变更
- 项目结构重组:
  - 验收文档 → claudedocs/
  - 测试脚本 → scripts/
  - 保持根目录整洁

### Security - 安全
- Systemd 安全加固配置
- Docker 容器权限限制
- 配置文件敏感信息保护
- 日志敏感字段过滤

## 统计数据

### 代码量
- Python 代码: 3,788 行
- 测试代码: 包含在上述统计中
- 文档: 1,000+ 行

### 文件组织
- 源代码: 7 个模块
- 测试文件: 7 个测试套件
- 运维脚本: 15 个工具脚本
- 配置文件: 8 个部署配置

### 提交历史
- Git 提交: 20+
- 主要功能分支: 3+
- 代码审查: 已完成

## 版本规划

### [0.2.0] - 计划中
- [ ] 支持更多交易所
- [ ] 自定义指标插件系统
- [ ] Web UI 控制面板
- [ ] 告警策略回测

### [0.3.0] - 远期规划
- [ ] 多策略并行运行
- [ ] 机器学习信号优化
- [ ] 告警历史分析
- [ ] RESTful API

---

[Unreleased]: https://github.com/username/signal/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/username/signal/releases/tag/v0.1.0
