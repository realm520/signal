#!/usr/bin/env python3
"""Health check script for Signal monitoring system.

Usage:
    python scripts/health_check.py

Exit codes:
    0 - Healthy
    1 - Unhealthy (log file issues, stale logs, etc.)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

def check_log_file() -> tuple[bool, str]:
    """Check if log file exists and has recent entries.

    Returns:
        (is_healthy, message)
    """
    log_file = Path("logs/signal.log")

    if not log_file.exists():
        return False, f"❌ Log file not found: {log_file}"

    # Check file size
    size_mb = log_file.stat().st_size / (1024 * 1024)
    if size_mb > 100:
        return False, f"⚠️  Log file too large: {size_mb:.1f}MB (rotation recommended)"

    # Check last modification time
    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
    now = datetime.now()
    age = now - mtime

    # If log hasn't been written in 5 minutes, something might be wrong
    if age > timedelta(minutes=5):
        return False, f"❌ Stale log file (last modified: {age.total_seconds():.0f}s ago)"

    # Try to read last few lines
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if not lines:
                return False, "❌ Log file is empty"

            last_line = lines[-1]
            if "error" in last_line.lower() or "exception" in last_line.lower():
                return False, f"⚠️  Recent errors detected in logs"
    except Exception as e:
        return False, f"❌ Cannot read log file: {e}"

    return True, f"✅ Log file healthy (size: {size_mb:.2f}MB, age: {age.total_seconds():.0f}s)"


def check_config_file() -> tuple[bool, str]:
    """Check if configuration file exists.

    Returns:
        (is_healthy, message)
    """
    config_file = Path("config.yaml")

    if not config_file.exists():
        return False, f"❌ Configuration file not found: {config_file}"

    return True, f"✅ Configuration file exists"


def main() -> int:
    """Run health checks.

    Returns:
        0 if healthy, 1 if unhealthy
    """
    print("🏥 Signal Health Check")
    print("=" * 60)

    checks = [
        ("Configuration", check_config_file),
        ("Log File", check_log_file),
    ]

    all_healthy = True

    for check_name, check_func in checks:
        is_healthy, message = check_func()
        print(f"\n{check_name}:")
        print(f"  {message}")

        if not is_healthy:
            all_healthy = False

    print("\n" + "=" * 60)

    if all_healthy:
        print("✅ All health checks passed")
        return 0
    else:
        print("❌ Some health checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
