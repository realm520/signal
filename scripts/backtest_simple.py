#!/usr/bin/env python3
"""Simple backtesting tool for Signal alert strategy.

Tests the alert strategy against historical data to evaluate effectiveness.

Usage:
    python scripts/backtest_simple.py [--symbol BTC/USDT] [--days 30]
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from signal_app.indicators import IndicatorEngine, OHLCV
from signal_app.alerts import AlertManager


class BacktestResult:
    """Backtest result container."""

    def __init__(self):
        self.total_alerts = 0
        self.bullish_alerts = 0
        self.bearish_alerts = 0
        self.alert_times = []
        self.alert_details = []

    def add_alert(self, alert_type: str, timestamp: int, price: float, details: dict):
        """Record an alert.

        Args:
            alert_type: "bullish" or "bearish"
            timestamp: Unix timestamp
            price: Price at alert time
            details: Additional alert details
        """
        self.total_alerts += 1
        if alert_type == "bullish":
            self.bullish_alerts += 1
        else:
            self.bearish_alerts += 1

        self.alert_times.append(timestamp)
        self.alert_details.append({
            'type': alert_type,
            'timestamp': timestamp,
            'price': price,
            **details
        })


def generate_sample_data(days: int = 30) -> list[OHLCV]:
    """Generate sample OHLCV data for backtesting.

    Note: This is simulated data. For real backtesting, use actual historical data.

    Args:
        days: Number of days to generate

    Returns:
        List of OHLCV bars
    """
    print(f"\n⚠️  注意: 使用模拟数据进行回测")
    print(f"   真实回测请使用历史K线数据")
    print()

    bars = []
    base_price = 40000.0
    base_volume = 1000.0
    bars_per_day = 96  # 24h * 4 (15min bars)

    total_bars = days * bars_per_day

    for i in range(total_bars):
        # Base price with gradual trend
        trend = i / total_bars * 3000
        base = base_price + trend

        # Create clear breakout patterns
        volume_mult = 1.0
        price_offset = 0

        # Strong bullish breakout (volume + price surge creating new high)
        if i % 50 == 40 and i > 35:
            volume_mult = 5.0
            price_offset = 800  # Strong price jump
        # Strong bearish breakdown (volume + price drop creating new low)
        elif i % 50 == 45 and i > 35:
            volume_mult = 4.8
            price_offset = -800  # Strong price drop

        price = base + price_offset
        volatility = 50  # Smaller base volatility

        bar = OHLCV(
            timestamp=int(datetime.now().timestamp()) - (total_bars - i) * 900,
            open=price - volatility,
            high=price + volatility * 2,
            low=price - volatility * 2,
            close=price,
            volume=base_volume * volume_mult
        )
        bars.append(bar)

    return bars


def run_backtest(
    bars: list[OHLCV],
    ma_period: int = 30,
    ma_type: str = "SMA",
    volume_threshold: float = 3.0,
    lookback_bars: int = 4
) -> BacktestResult:
    """Run backtest on historical data.

    Args:
        bars: Historical OHLCV bars
        ma_period: MA period
        ma_type: MA type (SMA/EMA)
        volume_threshold: Volume surge threshold
        lookback_bars: Lookback period for new high/low

    Returns:
        BacktestResult object
    """
    result = BacktestResult()

    # Create engine and alert manager
    engine = IndicatorEngine(
        ma_period=ma_period,
        ma_type=ma_type,
        volume_threshold=volume_threshold,
        lookback_bars=lookback_bars
    )

    # Note: AlertManager check_alert_conditions is synchronous
    cooldown_tracker = {}
    cooldown_seconds = 300  # 5 minutes

    print(f"📊 回测配置:")
    print(f"   K线数量: {len(bars)}")
    print(f"   MA周期: {ma_period}")
    print(f"   MA类型: {ma_type}")
    print(f"   成交量阈值: {volume_threshold}x")
    print(f"   回溯周期: {lookback_bars}")
    print()

    print("🔄 处理历史数据...\n")

    for i, bar in enumerate(bars):
        engine.add_bar(bar)

        # Skip if insufficient data
        if not engine.has_sufficient_data():
            continue

        # Calculate indicators
        ma_value = engine.calculate_ma()
        volume_surge, vol_mult = engine.check_volume_surge()
        is_new_high, prev_high = engine.check_new_high()
        is_new_low, prev_low = engine.check_new_low()

        current_price = engine.current_price

        # Check alert conditions (simplified from AlertManager)
        market_key = "BTC/USDT"

        # Check cooldown
        if market_key in cooldown_tracker:
            if bar.timestamp - cooldown_tracker[market_key] < cooldown_seconds:
                continue

        # Alert logic
        alert_type = None
        if volume_surge:
            if current_price > ma_value and is_new_high:
                alert_type = "bullish"
            elif current_price < ma_value and is_new_low:
                alert_type = "bearish"

        if alert_type:
            cooldown_tracker[market_key] = bar.timestamp

            result.add_alert(
                alert_type=alert_type,
                timestamp=bar.timestamp,
                price=current_price,
                details={
                    'ma': ma_value,
                    'volume_mult': vol_mult,
                    'prev_high': prev_high,
                    'prev_low': prev_low
                }
            )

            # Print progress every 10 alerts
            if result.total_alerts % 10 == 1:
                dt = datetime.fromtimestamp(bar.timestamp)
                print(f"   告警 #{result.total_alerts}: {alert_type} @ {dt.strftime('%Y-%m-%d %H:%M')} ${current_price:.2f}")

    return result


def print_backtest_results(result: BacktestResult, bars: list[OHLCV]):
    """Print backtest results.

    Args:
        result: BacktestResult object
        bars: Historical bars used
    """
    print("\n" + "=" * 70)
    print("📊 回测结果")
    print("=" * 70)

    if result.total_alerts == 0:
        print("\n⚠️  未触发任何告警")
        print("   可能的原因:")
        print("   - 市场波动不够大")
        print("   - 成交量阈值过高")
        print("   - 数据周期太短")
        return

    # Basic statistics
    print(f"\n📈 告警统计:")
    print(f"   总告警数: {result.total_alerts}")
    print(f"   看涨告警: {result.bullish_alerts} ({result.bullish_alerts/result.total_alerts*100:.1f}%)")
    print(f"   看跌告警: {result.bearish_alerts} ({result.bearish_alerts/result.total_alerts*100:.1f}%)")

    # Time analysis
    if len(result.alert_times) > 1:
        intervals = []
        for i in range(1, len(result.alert_times)):
            interval = (result.alert_times[i] - result.alert_times[i-1]) / 60  # minutes
            intervals.append(interval)

        avg_interval = sum(intervals) / len(intervals)
        print(f"\n⏱️  时间分析:")
        print(f"   平均告警间隔: {avg_interval:.1f} 分钟")
        print(f"   最短间隔: {min(intervals):.1f} 分钟")
        print(f"   最长间隔: {max(intervals):.1f} 分钟")

    # Recent alerts
    print(f"\n🔔 最近5个告警:")
    for alert in result.alert_details[-5:]:
        dt = datetime.fromtimestamp(alert['timestamp'])
        icon = "🚀" if alert['type'] == "bullish" else "📉"
        print(f"   {icon} {dt.strftime('%Y-%m-%d %H:%M')} | {alert['type']:8s} | ${alert['price']:.2f} | MA:{alert['ma']:.2f} | Vol:{alert['volume_mult']:.1f}x")

    print("\n" + "=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simple backtesting for Signal alert strategy"
    )
    parser.add_argument(
        '--symbol',
        type=str,
        default='BTC/USDT',
        help='Trading symbol (default: BTC/USDT)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to backtest (default: 30)'
    )
    parser.add_argument(
        '--ma-period',
        type=int,
        default=30,
        help='MA period (default: 30)'
    )
    parser.add_argument(
        '--volume-threshold',
        type=float,
        default=3.0,
        help='Volume threshold multiplier (default: 3.0)'
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🔬 Signal 策略回测")
    print("=" * 70)
    print(f"\n交易对: {args.symbol}")
    print(f"回测周期: {args.days} 天")

    # Generate sample data
    bars = generate_sample_data(days=args.days)

    # Run backtest
    result = run_backtest(
        bars=bars,
        ma_period=args.ma_period,
        volume_threshold=args.volume_threshold
    )

    # Print results
    print_backtest_results(result, bars)

    print("\n💡 提示:")
    print("   - 这是简化的回测工具，使用模拟数据")
    print("   - 真实回测需要使用历史K线数据")
    print("   - 回测结果不代表未来表现")
    print("   - 建议先纸上交易验证策略")
    print()


if __name__ == "__main__":
    main()
