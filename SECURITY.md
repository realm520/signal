# 安全最佳实践

## 配置安全

### Webhook URL 保护

**❌ 不要**将 Webhook URL 直接写入配置文件并提交到版本控制:
```yaml
alerts:
  lark_webhook: "https://open.larksuite.com/open-apis/bot/v2/hook/abc123..."  # 危险!
```

**✅ 推荐**使用环境变量:
```yaml
alerts:
  lark_webhook: "${LARK_WEBHOOK_URL}"
```

然后在环境中设置:
```bash
export LARK_WEBHOOK_URL="https://open.larksuite.com/..."
```

### API 密钥管理

如果将来添加交易所 API 密钥功能,遵循以下原则:

1. **永远不要**将密钥提交到 Git
2. 使用环境变量或密钥管理服务
3. 定期轮换密钥
4. 为不同环境使用不同的密钥

## 网络安全

### HTTPS 要求

- ✅ Lark Webhook 必须使用 HTTPS
- ✅ 所有外部 API 调用使用 TLS/SSL
- ✅ 验证 SSL 证书(不要禁用验证)

### 防火墙规则

推荐的防火墙配置:

```bash
# 允许 Prometheus exporter (如果需要)
sudo ufw allow 9090/tcp comment 'Signal Prometheus exporter'

# 限制访问来源(推荐)
sudo ufw allow from 10.0.0.0/8 to any port 9090 proto tcp

# 阻止所有其他入站连接
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

## 部署安全

### Docker 安全

**使用非 root 用户**:
```dockerfile
FROM python:3.11-slim
RUN useradd -m -u 1000 signal
USER signal
```

**限制容器权限**:
```yaml
# docker-compose.yml
services:
  signal:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

### Systemd 安全加固

已在 `scripts/signal.service` 中配置:

- ✅ `NoNewPrivileges=true` - 防止权限提升
- ✅ `PrivateTmp=true` - 隔离临时目录
- ✅ `ProtectSystem=strict` - 系统目录只读
- ✅ `ProtectHome=true` - 保护用户主目录
- ✅ `ReadWritePaths=/opt/signal/logs` - 最小写入权限

## 日志安全

### 敏感信息过滤

确保日志不包含:
- ❌ Webhook URL
- ❌ API 密钥
- ❌ 用户密码
- ❌ 个人身份信息

当前实现已自动过滤敏感字段。

### 日志访问控制

```bash
# 设置日志文件权限
chmod 640 logs/signal.log
chown signal:signal logs/signal.log

# 限制日志目录访问
chmod 750 logs/
```

## 依赖安全

### 定期更新

```bash
# 检查过期依赖
uv pip list --outdated

# 更新依赖
uv sync --upgrade

# 运行测试验证
uv run pytest
```

### 安全扫描

```bash
# 使用 pip-audit 扫描已知漏洞
pip install pip-audit
pip-audit

# 或使用 safety
pip install safety
safety check
```

## 监控安全

### Prometheus Exporter

如果暴露到公网:

1. **启用认证**:
```python
# 在 prometheus_exporter.py 中添加 Basic Auth
```

2. **使用反向代理**:
```nginx
location /metrics {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:9090;
}
```

3. **限制 IP 访问**:
```bash
# 仅允许 Prometheus 服务器访问
iptables -A INPUT -p tcp --dport 9090 -s 10.0.1.5 -j ACCEPT
iptables -A INPUT -p tcp --dport 9090 -j DROP
```

## 应急响应

### Webhook 泄露处理

如果 Webhook URL 意外泄露:

1. 立即在飞书管理后台重新生成 Webhook
2. 更新所有部署环境的配置
3. 审查日志查找可疑活动
4. 轮换所有相关凭证

### 安全事件报告

如发现安全漏洞,请:
1. **不要**公开披露
2. 发送邮件到项目维护者
3. 提供详细的复现步骤
4. 等待修复后再公开

## 合规性

### 数据保护

Signal 不收集或存储:
- ❌ 用户个人信息
- ❌ 交易凭证
- ❌ 财务数据

仅处理:
- ✅ 公开市场数据
- ✅ 技术指标
- ✅ 告警消息

### 审计日志

所有重要事件已记录:
- ✅ 程序启动/停止
- ✅ 配置加载
- ✅ 告警触发和发送
- ✅ 错误和异常

## 安全检查清单

部署前检查:

- [ ] Webhook URL 使用环境变量
- [ ] 配置文件权限正确 (640)
- [ ] 日志目录权限限制 (750)
- [ ] 防火墙规则已配置
- [ ] Systemd 安全选项已启用
- [ ] 依赖已更新到最新安全版本
- [ ] 所有测试通过
- [ ] 健康检查正常

运行时监控:

- [ ] 定期检查日志异常
- [ ] 监控告警频率
- [ ] 验证 Webhook 消息送达
- [ ] 审查 Prometheus 指标

---

**安全是持续的过程,不是一次性任务。定期审查和更新这些实践。**
