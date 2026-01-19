"""Unit tests for alerts module.

Test coverage for alert condition checking and notification logic.
Target coverage: > 85%
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from signal_app.alerts import AlertManager, AlertType


class TestAlertManager:
    """Test cases for AlertManager."""

    def test_initialization(self):
        """Test alert manager initialization."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=300,
            rate_limit=10
        )
        assert manager.lark_webhook == "https://example.com/webhook"
        assert manager.cooldown_seconds == 300
        assert manager.rate_limit == 10
        assert len(manager._last_alert_time) == 0

    def test_check_alert_conditions_bullish(self):
        """Test bullish alert condition (TC-F03-01)."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=300
        )

        # Bullish: volume_surge=True, price > MA, new_high=True
        alert_type = manager.check_alert_conditions(
            exchange="binance",
            market="BTC/USDT",
            current_price=110.0,
            ma_value=100.0,
            volume_surge=True,
            volume_multiplier=3.5,
            is_new_high=True,
            is_new_low=False
        )

        assert alert_type == AlertType.BULLISH

    def test_check_alert_conditions_bearish(self):
        """Test bearish alert condition (TC-F03-02)."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=300
        )

        # Bearish: volume_surge=True, price < MA, new_low=True
        alert_type = manager.check_alert_conditions(
            exchange="binance",
            market="BTC/USDT",
            current_price=90.0,
            ma_value=100.0,
            volume_surge=True,
            volume_multiplier=4.0,
            is_new_high=False,
            is_new_low=True
        )

        assert alert_type == AlertType.BEARISH

    def test_check_alert_conditions_no_volume_surge(self):
        """Test no alert when volume surge missing (TC-F03-03)."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=300
        )

        # No volume surge
        alert_type = manager.check_alert_conditions(
            exchange="binance",
            market="BTC/USDT",
            current_price=110.0,
            ma_value=100.0,
            volume_surge=False,
            volume_multiplier=1.5,
            is_new_high=True,
            is_new_low=False
        )

        assert alert_type is None

    def test_check_alert_conditions_no_breakout(self):
        """Test no alert when price doesn't break (TC-F03-04)."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=300
        )

        # Volume surge but no new high
        alert_type = manager.check_alert_conditions(
            exchange="binance",
            market="BTC/USDT",
            current_price=101.0,
            ma_value=100.0,
            volume_surge=True,
            volume_multiplier=3.5,
            is_new_high=False,
            is_new_low=False
        )

        assert alert_type is None

    def test_check_alert_conditions_price_near_ma(self):
        """Test no alert when price near MA without breakout."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=300
        )

        # Price slightly above MA but no new high
        alert_type = manager.check_alert_conditions(
            exchange="binance",
            market="BTC/USDT",
            current_price=101.0,
            ma_value=100.0,
            volume_surge=True,
            volume_multiplier=3.5,
            is_new_high=False,
            is_new_low=False
        )

        assert alert_type is None

        # Price slightly below MA but no new low
        alert_type = manager.check_alert_conditions(
            exchange="binance",
            market="BTC/USDT",
            current_price=99.0,
            ma_value=100.0,
            volume_surge=True,
            volume_multiplier=3.5,
            is_new_high=False,
            is_new_low=False
        )

        assert alert_type is None

    def test_is_in_cooldown(self):
        """Test cooldown period check (TC-F03-05)."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=300
        )

        market_key = "binance:BTC/USDT"

        # Not in cooldown initially
        assert not manager.is_in_cooldown(market_key)

        # Simulate alert sent
        import time
        manager._last_alert_time[market_key] = time.time()

        # Should be in cooldown
        assert manager.is_in_cooldown(market_key)

        # Simulate time passing (before cooldown expires)
        manager._last_alert_time[market_key] = time.time() - 100
        assert manager.is_in_cooldown(market_key)

        # Simulate cooldown expired
        manager._last_alert_time[market_key] = time.time() - 400
        assert not manager.is_in_cooldown(market_key)

    def test_is_rate_limited(self):
        """Test rate limiting."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            rate_limit=3
        )

        import time
        current_time = time.time()

        # Not limited initially
        assert not manager.is_rate_limited()

        # Add 3 recent alerts
        manager._recent_alerts = [
            current_time - 10,
            current_time - 20,
            current_time - 30
        ]

        # Should be rate limited (3 alerts in last minute)
        assert manager.is_rate_limited()

        # Add old alert (should be filtered out)
        manager._recent_alerts = [
            current_time - 70  # > 60 seconds ago
        ]

        # Should not be rate limited
        assert not manager.is_rate_limited()

    @pytest.mark.asyncio
    async def test_send_alert_success(self):
        """Test successful alert sending."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=10
        )

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        manager._http_client = mock_client

        # Send alert
        success = await manager.send_alert(
            alert_type=AlertType.BULLISH,
            exchange="binance",
            market="BTC/USDT",
            current_price=45000.0,
            ma_value=44000.0,
            volume_multiplier=3.5,
            current_volume=1250.0,
            reference_price=44500.0
        )

        assert success is True
        assert "binance:BTC/USDT" in manager._last_alert_time
        assert len(manager._recent_alerts) == 1

    @pytest.mark.asyncio
    async def test_send_alert_cooldown_skip(self):
        """Test alert skipped during cooldown."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=300
        )

        import time
        market_key = "binance:BTC/USDT"
        manager._last_alert_time[market_key] = time.time()

        mock_client = AsyncMock()
        manager._http_client = mock_client

        # Should skip due to cooldown
        success = await manager.send_alert(
            alert_type=AlertType.BULLISH,
            exchange="binance",
            market="BTC/USDT",
            current_price=45000.0,
            ma_value=44000.0,
            volume_multiplier=3.5,
            current_volume=1250.0,
            reference_price=44500.0
        )

        assert success is False
        # HTTP client should not be called
        mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_alert_rate_limited(self):
        """Test alert skipped when rate limited."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            rate_limit=2
        )

        import time
        current_time = time.time()
        # Simulate 2 recent alerts
        manager._recent_alerts = [current_time - 10, current_time - 20]

        mock_client = AsyncMock()
        manager._http_client = mock_client

        # Should skip due to rate limit
        success = await manager.send_alert(
            alert_type=AlertType.BULLISH,
            exchange="binance",
            market="BTC/USDT",
            current_price=45000.0,
            ma_value=44000.0,
            volume_multiplier=3.5,
            current_volume=1250.0,
            reference_price=44500.0
        )

        assert success is False
        mock_client.post.assert_not_called()

    def test_format_lark_message_bullish(self):
        """Test Lark message formatting for bullish signal."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook"
        )

        payload = manager._format_lark_message(
            alert_type=AlertType.BULLISH,
            exchange="binance",
            market="BTC/USDT",
            current_price=45230.50,
            ma_value=44100.00,
            volume_multiplier=3.5,
            current_volume=1250.00,
            reference_price=44200.00,
            price_change_pct=2.34
        )

        assert payload["msg_type"] == "text"
        assert "向上插针" in payload["content"]["text"]
        assert "Binance" in payload["content"]["text"]
        assert "BTC/USDT" in payload["content"]["text"]
        assert "45,230.50" in payload["content"]["text"]
        assert "3.5x" in payload["content"]["text"]

    def test_format_lark_message_bearish(self):
        """Test Lark message formatting for bearish signal."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook"
        )

        payload = manager._format_lark_message(
            alert_type=AlertType.BEARISH,
            exchange="binance",
            market="ETH/USDT",
            current_price=2180.30,
            ma_value=2250.00,
            volume_multiplier=4.2,
            current_volume=850.50,
            reference_price=2200.00,
            price_change_pct=-0.90
        )

        assert payload["msg_type"] == "text"
        assert "向下插针" in payload["content"]["text"]
        assert "ETH/USDT" in payload["content"]["text"]
        assert "2,180.30" in payload["content"]["text"]
        assert "4.2x" in payload["content"]["text"]

    def test_format_lark_message_with_mention(self):
        """Test Lark message formatting with user mention."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            mention_user_id="ou_test123"
        )

        payload = manager._format_lark_message(
            alert_type=AlertType.BULLISH,
            exchange="binance",
            market="BTC/USDT",
            current_price=45230.50,
            ma_value=44100.00,
            volume_multiplier=3.5,
            current_volume=1250.00,
            reference_price=44200.00,
            price_change_pct=2.34
        )

        assert payload["msg_type"] == "text"
        # Verify @ mention is included
        assert '<at user_id="ou_test123"></at>' in payload["content"]["text"]
        assert "向上插针" in payload["content"]["text"]

    def test_initialization_with_mention_user_id(self):
        """Test alert manager initialization with mention_user_id."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            cooldown_seconds=300,
            rate_limit=10,
            mention_user_id="ou_test123"
        )
        assert manager.lark_webhook == "https://example.com/webhook"
        assert manager.cooldown_seconds == 300
        assert manager.rate_limit == 10
        assert manager.mention_user_id == "ou_test123"

    def test_format_lark_message_with_simple_username(self):
        """Test Lark message formatting with simple username (text display only)."""
        manager = AlertManager(
            lark_webhook="https://example.com/webhook",
            mention_user_id="ZhangHarry"  # 简单用户名，非 open_id
        )

        payload = manager._format_lark_message(
            alert_type=AlertType.BULLISH,
            exchange="binance",
            market="BTC/USDT",
            current_price=45230.50,
            ma_value=44100.00,
            volume_multiplier=3.5,
            current_volume=1250.00,
            reference_price=44200.00,
            price_change_pct=2.34
        )

        assert payload["msg_type"] == "text"
        # 验证简单文本 @ 格式
        assert '@ZhangHarry ' in payload["content"]["text"]
        # 不应该包含 <at> 标签
        assert '<at user_id=' not in payload["content"]["text"]
        assert "向上插针" in payload["content"]["text"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
