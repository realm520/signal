#!/usr/bin/env python3
"""Simple Prometheus metrics exporter for Signal monitoring system.

Exposes basic metrics about alert counts and system health.

Usage:
    python scripts/prometheus_exporter.py [--port 9090]

Metrics exposed:
    - signal_alerts_total{type="bullish|bearish"}
    - signal_health_status{component="log|config"}
"""

import argparse
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint."""

    def do_GET(self):
        """Handle GET request for /metrics."""
        if self.path != '/metrics':
            self.send_response(404)
            self.end_headers()
            return

        metrics = self.generate_metrics()

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4')
        self.end_headers()
        self.wfile.write(metrics.encode('utf-8'))

    def generate_metrics(self) -> str:
        """Generate Prometheus metrics.

        Returns:
            Formatted metrics string
        """
        lines = []

        # Alert counts
        alert_counts = self._count_alerts()
        lines.append('# HELP signal_alerts_total Total number of alerts sent')
        lines.append('# TYPE signal_alerts_total counter')
        for alert_type, count in alert_counts.items():
            lines.append(f'signal_alerts_total{{type="{alert_type}"}} {count}')

        # Health status
        health = self._check_health()
        lines.append('# HELP signal_health_status Health status of components (1=healthy, 0=unhealthy)')
        lines.append('# TYPE signal_health_status gauge')
        for component, status in health.items():
            lines.append(f'signal_health_status{{component="{component}"}} {int(status)}')

        # Log file age
        log_age = self._get_log_age()
        if log_age is not None:
            lines.append('# HELP signal_log_age_seconds Age of last log entry in seconds')
            lines.append('# TYPE signal_log_age_seconds gauge')
            lines.append(f'signal_log_age_seconds {log_age}')

        return '\n'.join(lines) + '\n'

    def _count_alerts(self) -> Dict[str, int]:
        """Count alerts from log file.

        Returns:
            Dictionary of alert counts by type
        """
        log_file = Path('logs/signal.log')
        counts = {'bullish': 0, 'bearish': 0}

        if not log_file.exists():
            return counts

        # Count alerts from last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)

        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get('event') == 'alert_sent':
                            # Check timestamp
                            timestamp_str = entry.get('timestamp', '')
                            try:
                                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                if timestamp < cutoff:
                                    continue
                            except (ValueError, AttributeError):
                                pass

                            alert_type = entry.get('alert_type', 'unknown')
                            if alert_type in counts:
                                counts[alert_type] += 1
                    except (json.JSONDecodeError, ValueError):
                        continue
        except Exception:
            pass

        return counts

    def _check_health(self) -> Dict[str, bool]:
        """Check health of components.

        Returns:
            Dictionary of component health statuses
        """
        health = {
            'config': Path('config.yaml').exists(),
            'log': False
        }

        # Check log file health
        log_file = Path('logs/signal.log')
        if log_file.exists():
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                age = datetime.now() - mtime
                # Log is healthy if modified in last 5 minutes
                health['log'] = age < timedelta(minutes=5)
            except Exception:
                health['log'] = False

        return health

    def _get_log_age(self) -> float | None:
        """Get age of log file in seconds.

        Returns:
            Age in seconds or None if unavailable
        """
        log_file = Path('logs/signal.log')
        if not log_file.exists():
            return None

        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            age = (datetime.now() - mtime).total_seconds()
            return age
        except Exception:
            return None

    def log_message(self, format, *args):
        """Suppress request logging."""
        pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Prometheus metrics exporter for Signal"
    )
    parser.add_argument(
        '--port',
        type=int,
        default=9090,
        help='Port to listen on (default: 9090)'
    )

    args = parser.parse_args()

    server = HTTPServer(('0.0.0.0', args.port), MetricsHandler)

    print(f"📊 Prometheus exporter running on port {args.port}")
    print(f"   Metrics endpoint: http://localhost:{args.port}/metrics")
    print(f"   Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹  Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
