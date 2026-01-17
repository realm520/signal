#!/usr/bin/env python3
"""Fetch historical OHLCV data from exchanges for backtesting.

Downloads real market data and saves it in a format compatible with
the backtesting tool.

Usage:
    python scripts/fetch_historical_data.py --symbol BTC/USDT --days 30
    python scripts/fetch_historical_data.py --symbol ETH/USDT --exchange okx --days 7
"""

import argparse
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import ccxt
except ImportError:
    print("❌ 错误: 未安装 ccxt 库")
    print("   运行: uv sync")
    sys.exit(1)


def fetch_ohlcv_data(
    exchange_name: str,
    symbol: str,
    timeframe: str = '15m',
    days: int = 30
) -> list[dict]:
    """Fetch historical OHLCV data from exchange.

    Args:
        exchange_name: Exchange name (binance, okx, bybit, etc.)
        symbol: Trading symbol (BTC/USDT, ETH/USDT, etc.)
        timeframe: Candle timeframe (15m, 1h, etc.)
        days: Number of days to fetch

    Returns:
        List of OHLCV bars as dictionaries
    """
    print(f"\n📊 获取历史数据")
    print("=" * 70)
    print(f"交易所: {exchange_name}")
    print(f"交易对: {symbol}")
    print(f"时间粒度: {timeframe}")
    print(f"回溯天数: {days}")
    print()

    # Create exchange instance
    try:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({
            'enableRateLimit': True,
            'timeout': 30000,
            'rateLimit': 2000,  # More conservative rate limiting
        })
    except AttributeError:
        print(f"❌ 错误: 不支持的交易所 '{exchange_name}'")
        print(f"   支持的交易所: binance, okx, bybit, huobi, etc.")
        sys.exit(1)

    # Check if exchange supports OHLCV
    if not exchange.has['fetchOHLCV']:
        print(f"❌ 错误: {exchange_name} 不支持获取K线数据")
        sys.exit(1)

    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    # Convert to milliseconds
    since = int(start_time.timestamp() * 1000)

    print(f"🔄 开始下载数据...")
    print(f"   时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")
    print()

    all_bars = []

    try:
        # Fetch data in batches
        while True:
            print(f"   获取中... (已下载 {len(all_bars)} 根K线)", end='\r')

            bars = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=1000
            )

            if not bars:
                break

            # Convert to our format
            for bar in bars:
                timestamp, open_price, high, low, close, volume = bar
                all_bars.append({
                    'timestamp': timestamp // 1000,  # Convert to seconds
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume
                })

            # Update since for next batch
            since = bars[-1][0] + 1

            # Check if we've reached the end
            if bars[-1][0] >= int(end_time.timestamp() * 1000):
                break

        print(f"\n✅ 成功下载 {len(all_bars)} 根K线数据")

    except ccxt.NetworkError as e:
        print(f"\n❌ 网络错误: {e}")
        print(f"\n💡 建议:")
        print(f"   - 检查网络连接")
        print(f"   - 尝试使用其他交易所: --exchange okx 或 --exchange bybit")
        print(f"   - 如果遇到限流，请稍后再试")
        sys.exit(1)
    except ccxt.ExchangeError as e:
        print(f"\n❌ 交易所错误: {e}")
        print(f"\n💡 建议:")
        print(f"   - 检查交易对是否正确 (如 BTC/USDT, ETH/USDT)")
        print(f"   - 尝试使用其他交易所: --exchange okx 或 --exchange bybit")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        sys.exit(1)

    return all_bars


def save_data(data: list[dict], output_file: str):
    """Save OHLCV data to JSON file.

    Args:
        data: List of OHLCV bars
        output_file: Output file path
    """
    # Create directory if needed
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n💾 数据已保存到: {output_file}")

    # Print file size
    file_size = output_path.stat().st_size
    if file_size < 1024:
        size_str = f"{file_size} B"
    elif file_size < 1024 * 1024:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size / (1024 * 1024):.1f} MB"

    print(f"   文件大小: {size_str}")


def print_data_summary(data: list[dict]):
    """Print summary of fetched data.

    Args:
        data: List of OHLCV bars
    """
    if not data:
        print("\n⚠️  没有数据")
        return

    print("\n" + "=" * 70)
    print("📈 数据摘要")
    print("=" * 70)

    # Basic stats
    print(f"\n总K线数: {len(data)}")

    # Time range
    start_time = datetime.fromtimestamp(data[0]['timestamp'])
    end_time = datetime.fromtimestamp(data[-1]['timestamp'])
    print(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")

    # Price range
    prices = [bar['close'] for bar in data]
    print(f"价格范围: ${min(prices):,.2f} ~ ${max(prices):,.2f}")

    # Volume stats
    volumes = [bar['volume'] for bar in data]
    avg_volume = sum(volumes) / len(volumes)
    print(f"平均成交量: {avg_volume:,.2f}")

    # Recent bars
    print(f"\n最近5根K线:")
    for bar in data[-5:]:
        dt = datetime.fromtimestamp(bar['timestamp'])
        print(f"   {dt.strftime('%Y-%m-%d %H:%M')} | O:{bar['open']:,.2f} H:{bar['high']:,.2f} L:{bar['low']:,.2f} C:{bar['close']:,.2f} V:{bar['volume']:,.0f}")

    print("\n" + "=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch historical OHLCV data for backtesting"
    )
    parser.add_argument(
        '--exchange',
        type=str,
        default='binance',
        help='Exchange name (default: binance)'
    )
    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='Trading symbol (e.g., BTC/USDT, ETH/USDT)'
    )
    parser.add_argument(
        '--timeframe',
        type=str,
        default='15m',
        help='Candle timeframe (default: 15m)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to fetch (default: 30)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: data/{exchange}_{symbol}_{days}d.json)'
    )

    args = parser.parse_args()

    # Generate default output filename
    if not args.output:
        # Sanitize symbol for filename
        safe_symbol = args.symbol.replace('/', '_')
        args.output = f"data/{args.exchange}_{safe_symbol}_{args.days}d.json"

    # Fetch data
    data = fetch_ohlcv_data(
        exchange_name=args.exchange,
        symbol=args.symbol,
        timeframe=args.timeframe,
        days=args.days
    )

    # Save data
    save_data(data, args.output)

    # Print summary
    print_data_summary(data)

    print("\n💡 使用此数据进行回测:")
    print(f"   python scripts/backtest_simple.py --data {args.output}")
    print()


if __name__ == "__main__":
    main()
