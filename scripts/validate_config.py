#!/usr/bin/env python3
"""Configuration validation tool for Signal.

Validates config.yaml against requirements and best practices.

Usage:
    python scripts/validate_config.py [--config path/to/config.yaml]
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from signal_app.config import Config


def validate_config(config_path: str) -> tuple[bool, list[str]]:
    """Validate configuration file.

    Args:
        config_path: Path to config file

    Returns:
        (is_valid, issues) tuple
    """
    issues = []

    # Check file exists
    if not Path(config_path).exists():
        issues.append(f"❌ Config file not found: {config_path}")
        return False, issues

    # Try to load config
    try:
        config = Config(config_path)
    except FileNotFoundError as e:
        issues.append(f"❌ Config file error: {e}")
        return False, issues
    except ValueError as e:
        issues.append(f"❌ Config validation error: {e}")
        return False, issues
    except Exception as e:
        issues.append(f"❌ Unexpected error loading config: {e}")
        return False, issues

    # Validate exchanges
    if not config.exchanges:
        issues.append("⚠️  No exchanges configured")
    else:
        enabled_count = sum(1 for ex in config.exchanges if ex.get('enabled', True))
        if enabled_count == 0:
            issues.append("⚠️  All exchanges are disabled")

        # Check each exchange
        for i, exchange in enumerate(config.exchanges):
            name = exchange.get('name', f'exchange_{i}')

            if not exchange.get('markets'):
                issues.append(f"⚠️  Exchange '{name}' has no markets configured")

            # Validate market format
            for market in exchange.get('markets', []):
                if '/' not in market:
                    issues.append(f"⚠️  Invalid market format '{market}' in exchange '{name}' (should be 'BASE/QUOTE')")

    # Validate indicators
    if config.ma_period < 2:
        issues.append(f"❌ MA period too small: {config.ma_period} (minimum: 2)")

    if config.ma_period > 200:
        issues.append(f"⚠️  MA period very large: {config.ma_period} (typical: 20-50)")

    if config.ma_type not in ['SMA', 'EMA']:
        issues.append(f"❌ Invalid MA type: {config.ma_type} (must be 'SMA' or 'EMA')")

    if config.volume_threshold < 1.0:
        issues.append(f"❌ Volume threshold too small: {config.volume_threshold} (minimum: 1.0)")

    if config.volume_threshold > 10.0:
        issues.append(f"⚠️  Volume threshold very high: {config.volume_threshold} (typical: 2.0-5.0)")

    if config.lookback_bars < 1:
        issues.append(f"❌ Lookback bars too small: {config.lookback_bars} (minimum: 1)")

    # Validate alerts
    if not config.lark_webhook:
        issues.append("❌ Lark webhook URL is required")
    elif not config.lark_webhook.startswith('https://'):
        issues.append("⚠️  Lark webhook should use HTTPS")

    if config.cooldown_seconds < 60:
        issues.append(f"⚠️  Cooldown period very short: {config.cooldown_seconds}s (recommended: 300s)")

    if config.cooldown_seconds > 3600:
        issues.append(f"⚠️  Cooldown period very long: {config.cooldown_seconds}s (recommended: 300-900s)")

    if config.rate_limit < 1:
        issues.append(f"❌ Rate limit too small: {config.rate_limit} (minimum: 1)")

    if config.rate_limit > 100:
        issues.append(f"⚠️  Rate limit very high: {config.rate_limit} (typical: 10-30)")

    # Check for environment variables
    if '${' in str(config.lark_webhook):
        issues.append("⚠️  Lark webhook contains unreplaced environment variable")

    return len([i for i in issues if i.startswith('❌')]) == 0, issues


def print_results(is_valid: bool, issues: list[str], config_path: str):
    """Print validation results.

    Args:
        is_valid: Whether config is valid
        issues: List of issues found
        config_path: Path to config file
    """
    print("🔍 Signal Configuration Validator")
    print("=" * 70)
    print(f"\nConfig file: {config_path}")

    if not issues:
        print("\n✅ Configuration is valid!")
        print("   No issues found.")
    else:
        print(f"\n📋 Found {len(issues)} issue(s):\n")
        for issue in issues:
            print(f"   {issue}")

    print("\n" + "=" * 70)

    if is_valid:
        print("✅ Configuration validation passed")
        print("   Ready for deployment")
    else:
        print("❌ Configuration validation failed")
        print("   Fix critical errors (❌) before deployment")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Signal configuration file"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )

    args = parser.parse_args()

    is_valid, issues = validate_config(args.config)
    print_results(is_valid, issues, args.config)

    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
