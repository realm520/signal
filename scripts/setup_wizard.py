#!/usr/bin/env python3
"""Interactive setup wizard for Signal configuration.

Guides users through creating a valid config.yaml file.

Usage:
    python scripts/setup_wizard.py
"""

import sys
import os
from pathlib import Path


def print_header():
    """Print welcome header."""
    print("\n" + "=" * 70)
    print("🚀 Signal Configuration Wizard")
    print("=" * 70)
    print("\nThis wizard will help you create a config.yaml file.")
    print("Press Ctrl+C at any time to cancel.\n")


def get_input(prompt: str, default: str = None, validator=None) -> str:
    """Get validated user input.

    Args:
        prompt: Input prompt
        default: Default value
        validator: Optional validation function

    Returns:
        User input
    """
    while True:
        if default:
            value = input(f"{prompt} [{default}]: ").strip() or default
        else:
            value = input(f"{prompt}: ").strip()

        if not value:
            print("  ⚠️  This field is required.")
            continue

        if validator:
            is_valid, error = validator(value)
            if not is_valid:
                print(f"  ⚠️  {error}")
                continue

        return value


def validate_url(url: str) -> tuple[bool, str]:
    """Validate webhook URL.

    Args:
        url: URL to validate

    Returns:
        (is_valid, error_message)
    """
    if not url.startswith("https://"):
        return False, "URL must start with https://"
    if "open.larksuite.com" not in url and "open.feishu.cn" not in url:
        return False, "URL should be a Lark/Feishu webhook"
    return True, ""


def validate_number(value: str, min_val=None, max_val=None) -> tuple[bool, str]:
    """Validate numeric input.

    Args:
        value: Value to validate
        min_val: Minimum value
        max_val: Maximum value

    Returns:
        (is_valid, error_message)
    """
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return False, f"Value must be >= {min_val}"
        if max_val is not None and num > max_val:
            return False, f"Value must be <= {max_val}"
        return True, ""
    except ValueError:
        return False, "Must be a number"


def select_exchanges() -> list[dict]:
    """Interactive exchange selection.

    Returns:
        List of exchange configurations
    """
    print("\n📊 Exchange Configuration")
    print("-" * 70)

    exchanges = []

    available_exchanges = [
        ("binance", "Binance (推荐，最流行)"),
        ("okx", "OKX"),
        ("bybit", "Bybit"),
    ]

    print("\n可用交易所:")
    for i, (name, desc) in enumerate(available_exchanges, 1):
        print(f"  {i}. {desc}")

    while True:
        choice = input("\n选择交易所 (输入序号，回车完成): ").strip()

        if not choice:
            if not exchanges:
                print("  ⚠️  至少选择一个交易所")
                continue
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(available_exchanges):
                exchange_name = available_exchanges[idx][0]

                # Check if already added
                if any(e['name'] == exchange_name for e in exchanges):
                    print(f"  ⚠️  {exchange_name} 已添加")
                    continue

                # Get markets for this exchange
                markets = select_markets(exchange_name)
                if markets:
                    exchanges.append({
                        'name': exchange_name,
                        'markets': markets,
                        'enabled': True
                    })
                    print(f"  ✅ 已添加 {exchange_name} 交易所")
            else:
                print("  ⚠️  无效选择")
        except ValueError:
            print("  ⚠️  请输入数字")

    return exchanges


def select_markets(exchange_name: str) -> list[str]:
    """Select markets for an exchange.

    Args:
        exchange_name: Exchange name

    Returns:
        List of market symbols
    """
    print(f"\n  配置 {exchange_name} 的交易对:")

    popular_markets = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]
    markets = []

    print("\n  热门交易对:")
    for i, market in enumerate(popular_markets, 1):
        print(f"    {i}. {market}")

    print(f"    {len(popular_markets)+1}. 自定义")

    while True:
        choice = input(f"\n  选择交易对 (输入序号，回车完成): ").strip()

        if not choice:
            if not markets:
                print("    ⚠️  至少选择一个交易对")
                continue
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(popular_markets):
                market = popular_markets[idx]
                if market not in markets:
                    markets.append(market)
                    print(f"    ✅ 已添加 {market}")
                else:
                    print(f"    ⚠️  {market} 已添加")
            elif idx == len(popular_markets):
                # Custom market
                custom = input("    输入交易对 (如 BTC/USDT): ").strip().upper()
                if '/' in custom:
                    if custom not in markets:
                        markets.append(custom)
                        print(f"    ✅ 已添加 {custom}")
                    else:
                        print(f"    ⚠️  {custom} 已添加")
                else:
                    print("    ⚠️  格式错误，应为 BASE/QUOTE")
            else:
                print("    ⚠️  无效选择")
        except ValueError:
            print("    ⚠️  请输入数字")

    return markets


def configure_indicators() -> dict:
    """Configure indicator parameters.

    Returns:
        Indicator configuration
    """
    print("\n📈 指标配置")
    print("-" * 70)

    ma_period = int(get_input(
        "MA 周期 (K线数量)",
        default="30",
        validator=lambda v: validate_number(v, min_val=2, max_val=200)
    ))

    ma_types = ["SMA", "EMA"]
    print("\nMA 类型:")
    for i, ma_type in enumerate(ma_types, 1):
        desc = "简单移动平均" if ma_type == "SMA" else "指数移动平均"
        print(f"  {i}. {ma_type} ({desc})")

    ma_choice = int(get_input("选择 MA 类型", default="1")) - 1
    ma_type = ma_types[ma_choice] if 0 <= ma_choice < len(ma_types) else "SMA"

    volume_threshold = float(get_input(
        "成交量阈值 (倍数)",
        default="3.0",
        validator=lambda v: validate_number(v, min_val=1.0, max_val=10.0)
    ))

    lookback_bars = int(get_input(
        "回溯K线数 (用于新高新低)",
        default="4",
        validator=lambda v: validate_number(v, min_val=1, max_val=20)
    ))

    return {
        'ma_period': ma_period,
        'ma_type': ma_type,
        'volume_threshold': volume_threshold,
        'lookback_bars': lookback_bars
    }


def configure_alerts() -> dict:
    """Configure alert parameters.

    Returns:
        Alert configuration
    """
    print("\n🔔 告警配置")
    print("-" * 70)

    lark_webhook = get_input(
        "飞书 Webhook URL",
        validator=validate_url
    )

    cooldown = int(get_input(
        "冷却期 (秒)",
        default="300",
        validator=lambda v: validate_number(v, min_val=60, max_val=3600)
    ))

    rate_limit = int(get_input(
        "速率限制 (条/分钟)",
        default="10",
        validator=lambda v: validate_number(v, min_val=1, max_val=100)
    ))

    return {
        'lark_webhook': lark_webhook,
        'cooldown_seconds': cooldown,
        'rate_limit': rate_limit
    }


def configure_logging() -> dict:
    """Configure logging parameters.

    Returns:
        Logging configuration
    """
    print("\n📝 日志配置")
    print("-" * 70)

    levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    print("\n日志级别:")
    for i, level in enumerate(levels, 1):
        print(f"  {i}. {level}")

    level_choice = int(get_input("选择日志级别", default="2")) - 1
    level = levels[level_choice] if 0 <= level_choice < len(levels) else "INFO"

    log_file = get_input("日志文件路径", default="logs/signal.log")

    return {
        'level': level,
        'file': log_file
    }


def generate_config(exchanges, indicators, alerts, logging) -> str:
    """Generate YAML configuration.

    Args:
        exchanges: Exchange configuration
        indicators: Indicator configuration
        alerts: Alert configuration
        logging: Logging configuration

    Returns:
        YAML configuration string
    """
    yaml_lines = ["# Signal Configuration", "# Generated by setup wizard\n"]

    # Exchanges
    yaml_lines.append("exchanges:")
    for exchange in exchanges:
        yaml_lines.append(f"  - name: {exchange['name']}")
        yaml_lines.append("    markets:")
        for market in exchange['markets']:
            yaml_lines.append(f"      - {market}")
        yaml_lines.append(f"    enabled: {str(exchange['enabled']).lower()}\n")

    # Indicators
    yaml_lines.append("indicators:")
    yaml_lines.append(f"  ma_period: {indicators['ma_period']}")
    yaml_lines.append(f"  ma_type: {indicators['ma_type']}")
    yaml_lines.append(f"  volume_threshold: {indicators['volume_threshold']}")
    yaml_lines.append(f"  lookback_bars: {indicators['lookback_bars']}\n")

    # Alerts
    yaml_lines.append("alerts:")
    yaml_lines.append(f'  lark_webhook: "{alerts["lark_webhook"]}"')
    yaml_lines.append(f"  cooldown_seconds: {alerts['cooldown_seconds']}")
    yaml_lines.append(f"  rate_limit: {alerts['rate_limit']}\n")

    # Logging
    yaml_lines.append("logging:")
    yaml_lines.append(f"  level: {logging['level']}")
    yaml_lines.append(f"  file: {logging['file']}")

    return "\n".join(yaml_lines)


def main():
    """Main entry point."""
    try:
        print_header()

        # Collect configuration
        exchanges = select_exchanges()
        indicators = configure_indicators()
        alerts = configure_alerts()
        logging = configure_logging()

        # Generate config
        config_yaml = generate_config(exchanges, indicators, alerts, logging)

        # Preview
        print("\n" + "=" * 70)
        print("📄 生成的配置")
        print("=" * 70)
        print(config_yaml)

        # Confirm
        print("\n" + "=" * 70)
        confirm = input("\n保存配置到 config.yaml? (y/n): ").strip().lower()

        if confirm == 'y':
            # Create logs directory if needed
            Path("logs").mkdir(exist_ok=True)

            # Write config
            with open("config.yaml", "w") as f:
                f.write(config_yaml)

            print("\n✅ 配置已保存到 config.yaml")
            print("\n下一步:")
            print("  1. 验证配置: python scripts/validate_config.py")
            print("  2. 运行程序: uv run signal")
            print("\n🚀 祝交易顺利!")
        else:
            print("\n❌ 配置未保存")

    except KeyboardInterrupt:
        print("\n\n⏹  向导已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
