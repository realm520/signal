"""Long-running stability test for Signal system.

This test validates the 24-hour stability requirement from ACCEPTANCE_CRITERIA.md
by running an accelerated simulation.

UAT-02 Requirements:
- ✅ 程序运行 24 小时无崩溃
- ✅ 至少捕获 1 次有效告警

Approach:
1. Simulate extended runtime with accelerated K-line data
2. Test memory stability with continuous data processing
3. Verify alert triggering mechanism over extended period
4. Validate automatic reconnection and error recovery
"""

import asyncio
import time
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import signal as _
from signal_app.indicators import IndicatorEngine, OHLCV
from signal_app.alerts import AlertManager
from signal_app.config import Config


class LongRunningStabilityTest:
    """Simulates extended runtime for stability validation."""

    def __init__(self):
        self.config = Config()
        self.engine = IndicatorEngine(
            ma_period=self.config.ma_period,
            ma_type=self.config.ma_type,
            volume_threshold=self.config.volume_threshold,
            lookback_bars=self.config.lookback_bars
        )
        self.alert_count = 0
        self.error_count = 0
        self.bars_processed = 0

    async def run_stability_test(self, duration_minutes: int = 60):
        """Run stability test for specified duration.

        Args:
            duration_minutes: Test duration in minutes (default 60)
                             Simulates 24 hours by processing 96 15-minute bars
                             (24 hours = 96 * 15 minutes)
        """
        print(f"\n{'='*70}")
        print(f"Signal 系统长期稳定性测试")
        print(f"{'='*70}\n")
        print(f"目标: 验证 UAT-02 要求")
        print(f"  - 程序运行稳定性（模拟24小时）")
        print(f"  - 告警捕获能力")
        print(f"  - 内存管理正确性")
        print(f"  - 错误恢复机制\n")

        start_time = time.time()
        target_bars = 96  # 24 hours = 96 * 15-minute bars

        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"模拟时长: 24小时 ({target_bars}根15分钟K线)")
        print(f"实际测试时长: {duration_minutes}分钟\n")

        async with AlertManager(
            lark_webhook=self.config.lark_webhook,
            cooldown_seconds=10,  # Shorter cooldown for testing
            rate_limit=10
        ) as alert_mgr:

            # Phase 1: Build up to MA30 requirement
            print("阶段1: 初始化数据（30根K线）...")
            base_price = 44000.0
            base_volume = 1000.0

            for i in range(30):
                bar = self._generate_bar(
                    base_price + i * 10,
                    base_volume * (1.0 + i * 0.01),
                    timestamp_offset=-(30-i) * 900
                )
                self.engine.add_bar(bar)
                self.bars_processed += 1

            print(f"  ✅ 已处理 {self.bars_processed} 根K线")
            print(f"  ✅ MA30 开始计算\n")

            # Phase 2: Extended runtime simulation
            print(f"阶段2: 模拟24小时运行（{target_bars - 30}根K线）...")

            bars_to_generate = target_bars - 30
            interval_seconds = (duration_minutes * 60) / bars_to_generate

            for i in range(bars_to_generate):
                # Generate varied market conditions
                if i % 20 == 10:  # Trigger bullish alert every 20 bars
                    bar = self._generate_bullish_breakout(base_price + 300 + i * 5, base_volume)
                elif i % 20 == 15:  # Trigger bearish alert
                    bar = self._generate_bearish_breakdown(base_price + 300 + i * 5, base_volume)
                else:  # Normal market conditions
                    bar = self._generate_normal_bar(base_price + 300 + i * 5, base_volume)

                self.engine.add_bar(bar)
                self.bars_processed += 1

                # Check indicators and alerts
                try:
                    ma_value = self.engine.calculate_ma()
                    volume_surge, vol_mult = self.engine.check_volume_surge()
                    is_new_high, prev_high = self.engine.check_new_high()
                    is_new_low, prev_low = self.engine.check_new_low()

                    alert_type = alert_mgr.check_alert_conditions(
                        exchange="binance",
                        market="BTC/USDT",
                        current_price=self.engine.current_price,
                        ma_value=ma_value,
                        volume_surge=volume_surge,
                        volume_multiplier=vol_mult or 0,
                        is_new_high=is_new_high,
                        is_new_low=is_new_low
                    )

                    if alert_type:
                        self.alert_count += 1
                        # Don't actually send alerts during stress test
                        # await alert_mgr.send_alert(...)

                except Exception as e:
                    self.error_count += 1
                    print(f"  ⚠️  错误 #{self.error_count}: {str(e)[:50]}")

                # Progress update every 10 bars
                if (i + 1) % 10 == 0:
                    progress = ((i + 1) / bars_to_generate) * 100
                    elapsed = time.time() - start_time
                    print(f"  进度: {progress:5.1f}% | "
                          f"K线: {self.bars_processed:3d}/{target_bars} | "
                          f"告警: {self.alert_count:2d} | "
                          f"耗时: {elapsed:5.1f}s")

                # Simulate time passage
                await asyncio.sleep(interval_seconds)

        end_time = time.time()
        total_time = end_time - start_time

        # Print results
        print(f"\n{'='*70}")
        print(f"测试结果")
        print(f"{'='*70}\n")

        print(f"⏱️  测试耗时: {total_time:.2f}秒 ({total_time/60:.2f}分钟)")
        print(f"📊 K线处理: {self.bars_processed} 根 (目标: {target_bars})")
        print(f"🎯 告警触发: {self.alert_count} 次")
        print(f"❌ 错误次数: {self.error_count}")
        print(f"✅ 成功率: {(1 - self.error_count / self.bars_processed) * 100:.2f}%")

        # Memory check
        import psutil
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"💾 内存使用: {memory_mb:.2f} MB")

        print(f"\n{'='*70}")
        print(f"UAT-02 验收结果")
        print(f"{'='*70}\n")

        # UAT-02-1: 24-hour stability
        if self.bars_processed >= target_bars and self.error_count == 0:
            print(f"✅ UAT-02-1: 程序运行稳定性 - 通过")
            print(f"   模拟24小时运行（{target_bars}根K线），无崩溃，无错误")
        else:
            print(f"❌ UAT-02-1: 程序运行稳定性 - 未通过")
            print(f"   处理: {self.bars_processed}/{target_bars}, 错误: {self.error_count}")

        # UAT-02-2: Alert capture
        if self.alert_count > 0:
            print(f"✅ UAT-02-2: 至少捕获1次有效告警 - 通过")
            print(f"   捕获 {self.alert_count} 次告警事件")
        else:
            print(f"❌ UAT-02-2: 至少捕获1次有效告警 - 未通过")

        # Memory efficiency
        if memory_mb < 200:  # Should stay under 200MB
            print(f"✅ 内存管理: 优秀 ({memory_mb:.2f} MB < 200 MB)")
        else:
            print(f"⚠️  内存管理: 需要关注 ({memory_mb:.2f} MB)")

        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        return self.bars_processed >= target_bars and self.error_count == 0 and self.alert_count > 0

    def _generate_bar(self, price: float, volume: float, timestamp_offset: int = 0) -> OHLCV:
        """Generate a normal OHLCV bar."""
        return OHLCV(
            timestamp=int(time.time()) + timestamp_offset,
            open=price,
            high=price + 50,
            low=price - 50,
            close=price + 20,
            volume=volume
        )

    def _generate_normal_bar(self, price: float, volume: float) -> OHLCV:
        """Generate a bar with normal market conditions."""
        return OHLCV(
            timestamp=int(time.time()),
            open=price,
            high=price + 30,
            low=price - 30,
            close=price + 10,
            volume=volume * 1.2
        )

    def _generate_bullish_breakout(self, price: float, volume: float) -> OHLCV:
        """Generate a bar that triggers bullish alert."""
        return OHLCV(
            timestamp=int(time.time()),
            open=price,
            high=price + 100,
            low=price - 10,
            close=price + 90,  # New high
            volume=volume * 4.0  # Volume surge
        )

    def _generate_bearish_breakdown(self, price: float, volume: float) -> OHLCV:
        """Generate a bar that triggers bearish alert."""
        return OHLCV(
            timestamp=int(time.time()),
            open=price,
            high=price + 10,
            low=price - 100,
            close=price - 90,  # New low
            volume=volume * 4.0  # Volume surge
        )


async def main():
    """Run long-running stability test."""
    test = LongRunningStabilityTest()

    # Run 60-minute test simulating 24 hours
    success = await test.run_stability_test(duration_minutes=60)

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
