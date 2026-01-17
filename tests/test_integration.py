"""Integration test for alert system."""

import asyncio
import sys
import os
import time

# Add src to path and avoid stdlib signal conflict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import after path setup
import signal as _
from signal.indicators import IndicatorEngine, OHLCV
from signal.alerts import AlertManager
from signal.config import Config


async def test_complete_alert_flow():
    """Test complete flow: indicators -> alert check -> notification."""
    print("🧪 Signal 系统集成测试")
    print("=" * 50)

    # Load config
    config = Config()
    print(f"\n✅ 配置加载成功")
    print(f"   交易所: {[e['name'] for e in config.exchanges]}")
    print(f"   市场: {config.exchanges[0]['markets']}")
    print(f"   MA 周期: {config.ma_period}")
    print(f"   成交量阈值: {config.volume_threshold}x")

    # Create indicator engine
    engine = IndicatorEngine(
        ma_period=config.ma_period,
        ma_type=config.ma_type,
        volume_threshold=config.volume_threshold,
        lookback_bars=config.lookback_bars
    )
    print(f"\n✅ 指标引擎创建成功")

    # Add test data simulating bullish breakout
    print(f"\n📊 模拟市场数据（看涨突破场景）...")
    base_price = 44000.0
    base_volume = 1000.0

    # Build up to MA30 requirement
    for i in range(30):
        bar = OHLCV(
            timestamp=int(time.time()) - (30 - i) * 900,  # 15 min intervals
            open=base_price + i * 10,
            high=base_price + i * 10 + 50,
            low=base_price + i * 10 - 50,
            close=base_price + i * 10 + 20,
            volume=base_volume * (1.0 + i * 0.01)
        )
        engine.add_bar(bar)

    print(f"   已添加 {engine.bar_count} 根 K 线")

    # Calculate indicators before breakout
    ma_value = engine.calculate_ma()
    print(f"   当前 MA30: ${ma_value:,.2f}")
    print(f"   当前价格: ${engine.current_price:,.2f}")

    # Add breakout bars with volume surge
    print(f"\n🚀 触发看涨突破...")

    # Add 3 normal bars
    for i in range(3):
        bar = OHLCV(
            timestamp=int(time.time()) - (3 - i) * 900,
            open=base_price + 310 + i * 5,
            high=base_price + 320 + i * 5,
            low=base_price + 305 + i * 5,
            close=base_price + 315 + i * 5,
            volume=base_volume * 1.3
        )
        engine.add_bar(bar)

    # Add breakout bar with volume surge
    breakout_bar = OHLCV(
        timestamp=int(time.time()),
        open=base_price + 330,
        high=base_price + 360,
        low=base_price + 325,
        close=base_price + 350,  # New high
        volume=base_volume * 4.5  # 3.5x average of last 3 bars
    )
    engine.add_bar(breakout_bar)

    # Recalculate indicators
    ma_value = engine.calculate_ma()
    volume_surge, vol_mult = engine.check_volume_surge()
    is_new_high, prev_high = engine.check_new_high()
    is_new_low, prev_low = engine.check_new_low()

    print(f"\n📈 指标计算结果:")
    print(f"   当前价格: ${engine.current_price:,.2f}")
    print(f"   MA30: ${ma_value:,.2f}")
    print(f"   成交量放大: {volume_surge} ({vol_mult:.2f}x)")
    print(f"   新高: {is_new_high} (前高: ${prev_high:,.2f})")
    print(f"   新低: {is_new_low}")

    # Check alert conditions
    async with AlertManager(
        lark_webhook=config.lark_webhook,
        cooldown_seconds=10,
        rate_limit=10
    ) as alert_mgr:

        alert_type = alert_mgr.check_alert_conditions(
            exchange="binance",
            market="BTC/USDT",
            current_price=engine.current_price,
            ma_value=ma_value,
            volume_surge=volume_surge,
            volume_multiplier=vol_mult or 0,
            is_new_high=is_new_high,
            is_new_low=is_new_low
        )

        print(f"\n🔔 告警判断结果:")
        if alert_type:
            print(f"   告警类型: {alert_type}")
            print(f"   ✅ 满足所有告警条件！")

            # Send actual alert
            print(f"\n📤 发送告警到飞书...")
            success = await alert_mgr.send_alert(
                alert_type=alert_type,
                exchange="binance",
                market="BTC/USDT (测试)",
                current_price=engine.current_price,
                ma_value=ma_value,
                volume_multiplier=vol_mult or 0,
                current_volume=engine.current_volume,
                reference_price=prev_high or engine.current_price
            )

            if success:
                print(f"   ✅ 告警发送成功！")
                print(f"   请检查飞书群聊是否收到消息")
            else:
                print(f"   ❌ 告警发送失败")
                return False
        else:
            print(f"   ❌ 未满足告警条件")
            print(f"   检查: 成交量={volume_surge}, 价格>MA={engine.current_price > ma_value}, 新高={is_new_high}")
            return False

    print(f"\n{'=' * 50}")
    print(f"✅ 集成测试完成！")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_complete_alert_flow())
    exit(0 if success else 1)
