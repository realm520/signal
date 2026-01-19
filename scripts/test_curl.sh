#!/bin/bash

# 测试 Lark @ 消息的 curl 命令

WEBHOOK_URL="https://open.larksuite.com/open-apis/bot/v2/hook/78a3abef-5c4c-4faa-8342-a537a0820d12"
USER_ID="ou_9bc2ae52"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 测试 Lark @ 消息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Webhook: ${WEBHOOK_URL:0:60}..."
echo "User ID: $USER_ID"
echo ""
echo "发送测试消息..."
echo ""

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"msg_type\": \"text\",
    \"content\": {
      \"text\": \"<at user_id=\\\"$USER_ID\\\"></at> 🚀 测试消息\\n\\n这是一条测试 @ 消息，请确认是否收到通知。\\n\\n时间: $(date '+%Y-%m-%d %H:%M:%S')\"
    }
  }"

echo ""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 请求已发送！"
echo ""
echo "请检查 Lark 群聊："
echo "  1. 是否看到测试消息"
echo "  2. 是否有 @ 显示"
echo "  3. 是否收到通知"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
