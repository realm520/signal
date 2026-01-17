#!/usr/bin/env python3
"""System diagnostic tool for Signal.

Runs comprehensive checks and provides troubleshooting guidance.

Usage:
    python scripts/diagnose.py
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime


class Diagnostic:
    """Diagnostic runner."""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passes = []

    def check(self, name: str, passed: bool, message: str, fix: str = None):
        """Record check result.

        Args:
            name: Check name
            passed: Whether check passed
            message: Result message
            fix: Optional fix suggestion
        """
        if passed:
            self.passes.append(f"✅ {name}: {message}")
        else:
            self.issues.append({
                'name': name,
                'message': message,
                'fix': fix
            })

    def warn(self, name: str, message: str, suggestion: str = None):
        """Record warning.

        Args:
            name: Warning name
            message: Warning message
            suggestion: Optional suggestion
        """
        self.warnings.append({
            'name': name,
            'message': message,
            'suggestion': suggestion
        })


def check_python_version(diag: Diagnostic):
    """Check Python version."""
    version = sys.version_info
    required = (3, 10)

    if version >= required:
        diag.check(
            "Python版本",
            True,
            f"Python {version.major}.{version.minor}.{version.micro}"
        )
    else:
        diag.check(
            "Python版本",
            False,
            f"Python {version.major}.{version.minor} 太旧",
            f"需要 Python {required[0]}.{required[1]}+，请升级Python"
        )


def check_uv_installed(diag: Diagnostic):
    """Check if uv is installed."""
    try:
        result = subprocess.run(
            ['uv', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            diag.check("uv包管理器", True, version)
        else:
            diag.check(
                "uv包管理器",
                False,
                "uv命令失败",
                "运行: curl -LsSf https://astral.sh/uv/install.sh | sh"
            )
    except FileNotFoundError:
        diag.check(
            "uv包管理器",
            False,
            "未找到uv",
            "运行: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )
    except Exception as e:
        diag.check("uv包管理器", False, f"检查失败: {e}")


def check_config_file(diag: Diagnostic):
    """Check configuration file."""
    config_path = Path("config.yaml")

    if not config_path.exists():
        diag.check(
            "配置文件",
            False,
            "config.yaml不存在",
            "运行: python scripts/setup_wizard.py 或 cp config.example.yaml config.yaml"
        )
        return

    # Check file size
    size = config_path.stat().st_size
    if size == 0:
        diag.check(
            "配置文件",
            False,
            "config.yaml为空",
            "运行: python scripts/setup_wizard.py"
        )
        return

    # Check permissions
    if not os.access(config_path, os.R_OK):
        diag.check(
            "配置文件",
            False,
            "无法读取config.yaml",
            "运行: chmod 644 config.yaml"
        )
        return

    diag.check("配置文件", True, "config.yaml存在且可读")

    # Try to load and validate
    try:
        result = subprocess.run(
            ['python', 'scripts/validate_config.py'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            diag.check("配置验证", True, "配置有效")
        else:
            diag.check(
                "配置验证",
                False,
                "配置验证失败",
                "运行: python scripts/validate_config.py 查看详情"
            )
    except Exception as e:
        diag.warn("配置验证", f"无法运行验证: {e}")


def check_dependencies(diag: Diagnostic):
    """Check Python dependencies."""
    try:
        result = subprocess.run(
            ['uv', 'pip', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Check for key packages
            output = result.stdout.lower()
            required = ['ccxt', 'pandas', 'httpx', 'pyyaml', 'structlog']
            missing = [pkg for pkg in required if pkg not in output]

            if not missing:
                diag.check("依赖包", True, "所有必需依赖已安装")
            else:
                diag.check(
                    "依赖包",
                    False,
                    f"缺少依赖: {', '.join(missing)}",
                    "运行: uv sync"
                )
        else:
            diag.warn("依赖包", "无法列出依赖包")
    except Exception as e:
        diag.warn("依赖包", f"检查失败: {e}")


def check_logs_directory(diag: Diagnostic):
    """Check logs directory."""
    logs_dir = Path("logs")

    if not logs_dir.exists():
        diag.warn(
            "日志目录",
            "logs/目录不存在",
            "运行: mkdir logs"
        )
        return

    if not os.access(logs_dir, os.W_OK):
        diag.check(
            "日志目录",
            False,
            "logs/目录不可写",
            "运行: chmod 755 logs"
        )
        return

    diag.check("日志目录", True, "logs/目录存在且可写")

    # Check log file if exists
    log_file = logs_dir / "signal.log"
    if log_file.exists():
        # Check age
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        age = (datetime.now() - mtime).total_seconds()

        if age < 300:  # 5 minutes
            diag.check("日志文件", True, f"最近更新于{int(age)}秒前")
        elif age < 3600:  # 1 hour
            diag.warn(
                "日志文件",
                f"上次更新于{int(age/60)}分钟前",
                "程序可能未运行"
            )
        else:
            diag.warn(
                "日志文件",
                f"上次更新于{int(age/3600)}小时前",
                "程序可能已停止"
            )


def check_network_connectivity(diag: Diagnostic):
    """Check network connectivity."""
    # Check if we can resolve DNS
    try:
        import socket
        socket.gethostbyname("api.binance.com")
        diag.check("网络连接", True, "可以访问Binance API")
    except socket.gaierror:
        diag.check(
            "网络连接",
            False,
            "无法解析api.binance.com",
            "检查网络连接和DNS设置"
        )
    except Exception as e:
        diag.warn("网络连接", f"检查失败: {e}")


def check_webhook_config(diag: Diagnostic):
    """Check webhook configuration."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        return

    try:
        with open(config_path) as f:
            content = f.read()

        if '${LARK_WEBHOOK_URL}' in content:
            # Using environment variable
            webhook_url = os.getenv('LARK_WEBHOOK_URL')
            if webhook_url:
                diag.check("Webhook配置", True, "使用环境变量")
            else:
                diag.check(
                    "Webhook配置",
                    False,
                    "环境变量LARK_WEBHOOK_URL未设置",
                    "运行: export LARK_WEBHOOK_URL='your_webhook_url'"
                )
        elif 'https://open' in content:
            diag.check("Webhook配置", True, "已配置Webhook URL")
        else:
            diag.warn(
                "Webhook配置",
                "未找到Webhook URL",
                "检查config.yaml中的lark_webhook设置"
            )
    except Exception as e:
        diag.warn("Webhook配置", f"检查失败: {e}")


def check_tests(diag: Diagnostic):
    """Check if tests pass."""
    try:
        result = subprocess.run(
            ['uv', 'run', 'pytest', 'tests/', '-q'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            # Parse output
            if 'passed' in result.stdout:
                diag.check("测试套件", True, "所有测试通过")
            else:
                diag.warn("测试套件", "测试运行但结果不明确")
        else:
            diag.check(
                "测试套件",
                False,
                "测试失败",
                "运行: uv run pytest tests/ -v 查看详情"
            )
    except FileNotFoundError:
        diag.warn("测试套件", "pytest未安装或不在PATH中")
    except subprocess.TimeoutExpired:
        diag.warn("测试套件", "测试运行超时")
    except Exception as e:
        diag.warn("测试套件", f"无法运行测试: {e}")


def print_results(diag: Diagnostic):
    """Print diagnostic results."""
    print("\n" + "=" * 70)
    print("🔍 Signal 系统诊断报告")
    print("=" * 70)
    print(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Passes
    if diag.passes:
        print("✅ 通过的检查:\n")
        for msg in diag.passes:
            print(f"   {msg}")
        print()

    # Warnings
    if diag.warnings:
        print("⚠️  警告:\n")
        for warning in diag.warnings:
            print(f"   ⚠️  {warning['name']}: {warning['message']}")
            if warning.get('suggestion'):
                print(f"       建议: {warning['suggestion']}")
            print()

    # Issues
    if diag.issues:
        print("❌ 发现问题:\n")
        for issue in diag.issues:
            print(f"   ❌ {issue['name']}: {issue['message']}")
            if issue.get('fix'):
                print(f"       修复: {issue['fix']}")
            print()

    # Summary
    print("=" * 70)
    print("📊 总结")
    print("=" * 70)
    print(f"   通过: {len(diag.passes)}")
    print(f"   警告: {len(diag.warnings)}")
    print(f"   错误: {len(diag.issues)}")
    print()

    if not diag.issues:
        if not diag.warnings:
            print("✅ 系统状态良好，可以运行Signal")
        else:
            print("⚠️  存在一些警告，但系统可以运行")
    else:
        print("❌ 请修复上述问题后再运行Signal")

    print("\n" + "=" * 70 + "\n")


def main():
    """Main entry point."""
    diag = Diagnostic()

    print("\n🔍 运行系统诊断...\n")

    # Run all checks
    check_python_version(diag)
    check_uv_installed(diag)
    check_config_file(diag)
    check_dependencies(diag)
    check_logs_directory(diag)
    check_network_connectivity(diag)
    check_webhook_config(diag)
    check_tests(diag)

    # Print results
    print_results(diag)

    # Exit code
    sys.exit(1 if diag.issues else 0)


if __name__ == "__main__":
    main()
