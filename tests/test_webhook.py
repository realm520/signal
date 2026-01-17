"""Test Lark webhook functionality."""

import asyncio
import httpx


async def test_webhook():
    """Send test message to Lark webhook."""
    webhook_url = "https://open.larksuite.com/open-apis/bot/v2/hook/78a3abef-5c4c-4faa-8342-a537a0820d12"

    print("📡 测试飞书 Webhook 连接...")
    print(f"URL: {webhook_url[:60]}...")
    print()

    # Simple test message
    payload = {
        "msg_type": "text",
        "content": {
            "text": "🧪 Signal 系统测试消息\n\n这是一条测试消息，用于验证 Webhook 连接正常。\n\n⏰ 测试时间: 2026-01-17"
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()

            print("✅ 消息发送成功！")
            print(f"HTTP 状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            print()
            print("请检查飞书群聊是否收到测试消息")

    except httpx.HTTPError as e:
        print(f"❌ 发送失败: {e}")
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_webhook())
    exit(0 if success else 1)
