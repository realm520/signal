#!/usr/bin/env python3
"""Alert statistics analyzer for Signal monitoring system.

Analyzes log files to extract alert statistics and patterns.

Usage:
    python scripts/alert_stats.py [--days N] [--log FILE]
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Any


def parse_log_line(line: str) -> Dict[str, Any] | None:
    """Parse a structured log line (JSON format).

    Args:
        line: Log line string

    Returns:
        Parsed log entry or None if invalid
    """
    try:
        # Try JSON format first (structlog default)
        log_entry = json.loads(line)
        return log_entry
    except (json.JSONDecodeError, ValueError):
        return None


def extract_alert_events(log_file: Path, days: int = 7) -> List[Dict]:
    """Extract alert events from log file.

    Args:
        log_file: Path to log file
        days: Number of days to analyze

    Returns:
        List of alert event dictionaries
    """
    cutoff_time = datetime.now() - timedelta(days=days)
    alert_events = []

    try:
        with open(log_file, 'r') as f:
            for line in f:
                entry = parse_log_line(line.strip())
                if not entry:
                    continue

                event_type = entry.get('event', '')

                # Look for alert-related events
                if 'alert' in event_type.lower():
                    # Try to parse timestamp
                    timestamp_str = entry.get('timestamp', '')
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if timestamp < cutoff_time:
                            continue
                    except (ValueError, AttributeError):
                        pass

                    alert_events.append(entry)

    except FileNotFoundError:
        print(f"⚠️  Log file not found: {log_file}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Error reading log file: {e}", file=sys.stderr)

    return alert_events


def analyze_alerts(alert_events: List[Dict]) -> Dict[str, Any]:
    """Analyze alert events and generate statistics.

    Args:
        alert_events: List of alert event dictionaries

    Returns:
        Statistics dictionary
    """
    stats = {
        'total_alerts': len(alert_events),
        'by_type': Counter(),
        'by_exchange': Counter(),
        'by_market': Counter(),
        'by_hour': defaultdict(int),
        'recent_alerts': []
    }

    for event in alert_events:
        # Alert type (bullish/bearish)
        alert_type = event.get('alert_type', 'unknown')
        stats['by_type'][alert_type] += 1

        # Exchange
        exchange = event.get('exchange', 'unknown')
        stats['by_exchange'][exchange] += 1

        # Market
        market = event.get('market', 'unknown')
        stats['by_market'][market] += 1

        # Hour of day
        timestamp_str = event.get('timestamp', '')
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            hour = timestamp.hour
            stats['by_hour'][hour] += 1
        except (ValueError, AttributeError):
            pass

        # Keep last 10 alerts for display
        if len(stats['recent_alerts']) < 10:
            stats['recent_alerts'].append({
                'timestamp': event.get('timestamp', 'unknown'),
                'type': alert_type,
                'market': market,
                'price': event.get('current_price', 0)
            })

    return stats


def print_statistics(stats: Dict[str, Any], days: int) -> None:
    """Print formatted statistics.

    Args:
        stats: Statistics dictionary
        days: Number of days analyzed
    """
    print(f"📊 Alert Statistics (Last {days} days)")
    print("=" * 70)

    print(f"\n📈 Total Alerts: {stats['total_alerts']}")

    if stats['total_alerts'] == 0:
        print("\nNo alerts found in the specified time period.")
        return

    # By type
    print("\n🎯 By Alert Type:")
    for alert_type, count in stats['by_type'].most_common():
        percentage = (count / stats['total_alerts']) * 100
        icon = "🚀" if alert_type == "bullish" else "📉" if alert_type == "bearish" else "❓"
        print(f"  {icon} {alert_type:10s}: {count:3d} ({percentage:5.1f}%)")

    # By exchange
    print("\n🏦 By Exchange:")
    for exchange, count in stats['by_exchange'].most_common():
        percentage = (count / stats['total_alerts']) * 100
        print(f"  • {exchange:10s}: {count:3d} ({percentage:5.1f}%)")

    # By market
    print("\n💹 Top Markets:")
    for market, count in stats['by_market'].most_common(5):
        percentage = (count / stats['total_alerts']) * 100
        print(f"  • {market:15s}: {count:3d} ({percentage:5.1f}%)")

    # By hour
    print("\n🕐 Alerts by Hour:")
    for hour in range(24):
        count = stats['by_hour'].get(hour, 0)
        if count > 0:
            bar = "█" * min(int(count / max(stats['by_hour'].values()) * 30), 30)
            print(f"  {hour:02d}:00 | {bar} {count}")

    # Recent alerts
    if stats['recent_alerts']:
        print("\n🔔 Recent Alerts:")
        for alert in reversed(stats['recent_alerts']):
            icon = "🚀" if alert['type'] == "bullish" else "📉"
            print(f"  {icon} {alert['timestamp'][:19]} | {alert['market']:15s} | ${alert['price']:.2f}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Signal alert statistics from logs"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )
    parser.add_argument(
        '--log',
        type=Path,
        default=Path('logs/signal.log'),
        help='Path to log file (default: logs/signal.log)'
    )

    args = parser.parse_args()

    # Extract alert events
    alert_events = extract_alert_events(args.log, args.days)

    # Analyze and display statistics
    stats = analyze_alerts(alert_events)
    print_statistics(stats, args.days)


if __name__ == "__main__":
    main()
