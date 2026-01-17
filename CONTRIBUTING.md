# 贡献指南

感谢你对 Signal 项目的兴趣!

## 开发环境设置

### 1. Fork 和克隆

```bash
git clone https://github.com/your-username/signal.git
cd signal
```

### 2. 安装依赖

```bash
# 安装 uv (如果还没有)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync --all-extras
```

### 3. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml 设置你的 Webhook URL
```

## 开发流程

### 分支策略

- `main` - 稳定的生产代码
- `feature/*` - 新功能开发
- `fix/*` - Bug 修复
- `docs/*` - 文档更新

### 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 代码规范

#### Python 风格

遵循 PEP 8:

```bash
# 检查代码风格
uv run ruff check src/

# 自动格式化
uv run ruff format src/
```

#### 类型提示

所有新代码应包含类型提示:

```python
def calculate_ma(self, prices: list[float]) -> float:
    """Calculate moving average."""
    return sum(prices) / len(prices)
```

#### 文档字符串

使用 Google 风格的 docstrings:

```python
def send_alert(
    self,
    alert_type: str,
    market: str,
    price: float
) -> bool:
    """Send alert to Lark webhook.

    Args:
        alert_type: Type of alert ("bullish" or "bearish")
        market: Market symbol (e.g., "BTC/USDT")
        price: Current price

    Returns:
        True if alert sent successfully, False otherwise

    Raises:
        ValueError: If alert_type is invalid
    """
    pass
```

### 测试

#### 运行测试

```bash
# 运行所有测试
uv run pytest

# 详细输出
uv run pytest -v

# 指定测试文件
uv run pytest tests/test_indicators.py

# 运行特定测试
uv run pytest tests/test_indicators.py::TestIndicatorEngine::test_ma_calculation
```

#### 编写测试

所有新功能必须包含测试:

```python
import pytest
from signal_app.indicators import IndicatorEngine

class TestNewFeature:
    def test_basic_functionality(self):
        """Test basic functionality."""
        # Arrange
        engine = IndicatorEngine(ma_period=30)

        # Act
        result = engine.some_new_method()

        # Assert
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_feature(self):
        """Test async functionality."""
        # Your async test here
        pass
```

#### 测试覆盖率

目标: >80% 代码覆盖率

```bash
# 安装覆盖率工具
uv pip install pytest-cov

# 运行带覆盖率的测试
uv run pytest --cov=src/signal_app --cov-report=html

# 查看报告
open htmlcov/index.html
```

### 提交规范

使用语义化提交消息:

```
类型: 简短描述

详细说明(可选)

相关 Issue: #123
```

**类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式(不影响功能)
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具变更

**示例**:

```bash
git commit -m "feat: 添加 EMA 指标支持

实现指数移动平均(EMA)计算。
用户可以在 config.yaml 中配置 ma_type: EMA。

相关 Issue: #42"
```

## 提交 Pull Request

### 1. 推送分支

```bash
git push origin feature/your-feature-name
```

### 2. 创建 PR

在 GitHub 上创建 Pull Request,包含:

- **标题**: 清晰描述变更
- **描述**: 详细说明做了什么,为什么做
- **测试**: 说明如何测试变更
- **截图**: 如果有 UI 变更

### 3. PR 检查清单

- [ ] 代码符合风格规范 (`ruff check`)
- [ ] 所有测试通过 (`pytest`)
- [ ] 添加了新测试(如适用)
- [ ] 更新了文档(如适用)
- [ ] 提交消息清晰
- [ ] 没有合并冲突

### 4. Code Review

- 响应审查意见
- 进行必要的修改
- 保持耐心和开放心态

## 报告 Bug

### Bug 报告应包含

1. **环境信息**:
   - OS 和版本
   - Python 版本
   - Signal 版本

2. **复现步骤**:
   ```
   1. 配置 config.yaml 为...
   2. 运行命令 `uv run signal`
   3. 观察到错误 X
   ```

3. **预期行为**: 应该发生什么

4. **实际行为**: 实际发生了什么

5. **日志**: 相关的日志输出

6. **配置**: 相关的配置(移除敏感信息)

### 安全漏洞

**不要**公开报告安全漏洞。请参考 [SECURITY.md](SECURITY.md)。

## 功能请求

### 提出新功能前

1. 检查是否已有类似的 Issue
2. 考虑功能是否符合项目目标
3. 评估实现复杂度

### 功能请求应包含

1. **用例**: 为什么需要这个功能?
2. **提议方案**: 如何实现?
3. **替代方案**: 考虑过哪些其他方案?
4. **影响**: 对现有功能的影响?

## 文档

### 更新文档

当你的变更影响用户使用时:

- 更新 README.md
- 更新相关的配置示例
- 添加/更新 docstrings
- 考虑添加使用示例

### 文档风格

- 使用清晰、简洁的语言
- 提供代码示例
- 包含预期输出
- 解释"为什么",不仅仅是"如何"

## 发布流程

(仅维护者)

1. 更新版本号 (`pyproject.toml`)
2. 更新 CHANGELOG.md
3. 创建 Git tag
4. 构建 Docker 镜像
5. 发布到 PyPI(如果适用)

## 获取帮助

遇到问题?

- 查看 [README.md](README.md)
- 查看 [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md)
- 搜索现有 Issues
- 创建新 Issue 提问

## 行为准则

### 我们的承诺

- 保持友好和专业
- 尊重不同观点
- 接受建设性批评
- 专注于对项目最有利的事情

### 不可接受的行为

- 骚扰、歧视性言论
- 侮辱或贬损性评论
- 未经同意发布他人私人信息
- 其他不专业或不受欢迎的行为

---

**感谢你的贡献! 🚀**
