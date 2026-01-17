"""Test Lark webhook notification."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import signal as signal_module
from signal_module.config import Config
from signal_module.alerts import AlertManager


async def test_lark_notification():
    """Test sending a notification to Lark webhook."""
    # Load config
    config = Config()

    print(f"📡 测试飞书 Webhook 推送")
    print(f"Webhook URL: {config.lark_webhook[:50]}...")
    print()

    # Create alert manager
    async with AlertManager(
        lark_webhook=config.lark_webhook,
        cooldown_seconds=10,
        rate_limit=10
    ) as alert_mgr:

        # Test bullish alert
        print("🚀 发送看涨测试告警...")
        success = await alert_mgr.send_alert(
            alert_type="bullish",
            exchange="binance",
            market="BTC/USDT",
            current_price=45230.50,
            ma_value=44100.00,
            volume_multiplier=3.5,
            current_volume=1250.00,
            reference_price=44200.00
        )

        if success:
            print("✅ 看涨告警发送成功！请检查飞书消息")
        else:
            print("❌ 看涨告警发送失败")

        print()
        await asyncio.sleep(2)

        # Test bearish alert
        print("📉 发送看跌测试告警...")
        success = await alert_mgr.send_alert(
            alert_type="bearish",
            exchange="binance",
            market="ETH/USDT",
            current_price=2180.30,
            ma_value=2250.00,
            volume_multiplier=4.2,
            current_volume=850.50,
            reference_price=2200.00
        )

        if success:
            print("✅ 看跌告警发送成功！请检查飞书消息")
        else:
            print("❌ 看跌告警发送失败")

    print()
    print("✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_lark_notification())
