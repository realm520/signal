"""Alert condition checking and Lark notification module."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Optional
import httpx
import structlog

logger = structlog.get_logger()


class AlertType:
    """Alert type enumeration."""
    BULLISH = "bullish"
    BEARISH = "bearish"


class AlertManager:
    """Manage alert conditions and send notifications."""

    def __init__(
        self,
        lark_webhook: str,
        cooldown_seconds: int = 300,
        rate_limit: int = 10
    ):
        """Initialize alert manager.

        Args:
            lark_webhook: Lark webhook URL
            cooldown_seconds: Cooldown period in seconds
            rate_limit: Maximum messages per minute
        """
        self.lark_webhook = lark_webhook
        self.cooldown_seconds = cooldown_seconds
        self.rate_limit = rate_limit

        # Track last alert time for each market
        self._last_alert_time: Dict[str, float] = {}

        # Rate limiting
        self._recent_alerts: list[float] = []

        # HTTP client
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._http_client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()

    def check_alert_conditions(
        self,
        exchange: str,
        market: str,
        current_price: float,
        ma_value: float,
        volume_surge: bool,
        volume_multiplier: float,
        is_new_high: bool,
        is_new_low: bool
    ) -> Optional[str]:
        """Check if alert conditions are met.

        Returns:
            Alert type (bullish/bearish) or None if no alert
        """
        # Condition 1: Volume surge must be present
        if not volume_surge:
            return None

        # Condition 2a: Bullish signal (price > MA30 AND new high)
        if current_price > ma_value and is_new_high:
            return AlertType.BULLISH

        # Condition 2b: Bearish signal (price < MA30 AND new low)
        if current_price < ma_value and is_new_low:
            return AlertType.BEARISH

        return None

    def is_in_cooldown(self, market_key: str) -> bool:
        """Check if market is in cooldown period.

        Args:
            market_key: Market identifier (e.g., "binance:BTC/USDT")

        Returns:
            True if in cooldown period
        """
        if market_key not in self._last_alert_time:
            return False

        elapsed = time.time() - self._last_alert_time[market_key]
        return elapsed < self.cooldown_seconds

    def is_rate_limited(self) -> bool:
        """Check if rate limit is exceeded.

        Returns:
            True if rate limit exceeded
        """
        current_time = time.time()
        # Remove alerts older than 1 minute
        self._recent_alerts = [
            t for t in self._recent_alerts
            if current_time - t < 60
        ]

        return len(self._recent_alerts) >= self.rate_limit

    def _format_lark_message(
        self,
        alert_type: str,
        exchange: str,
        market: str,
        current_price: float,
        ma_value: float,
        volume_multiplier: float,
        current_volume: float,
        reference_price: float,
        price_change_pct: float
    ) -> dict:
        """Format message for Lark webhook.

        Args:
            alert_type: Alert type (bullish/bearish)
            exchange: Exchange name
            market: Market symbol
            current_price: Current price
            ma_value: MA30 value
            volume_multiplier: Volume surge multiplier
            current_volume: Current volume
            reference_price: Reference high/low price
            price_change_pct: Price change percentage

        Returns:
            Lark message payload
        """
        # Determine emoji and signal name
        if alert_type == AlertType.BULLISH:
            emoji = "🚀"
            signal = "看涨信号"
            direction = "↑"
            position = "上方"
        else:
            emoji = "📉"
            signal = "看跌信号"
            direction = "↓"
            position = "下方"

        # Format timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Build message content
        content = f"""{emoji} **{signal}** | {exchange.capitalize()}
📊 **{market}**: ${current_price:,.2f} {direction} {price_change_pct:+.2f}%

📈 **指标**:
- 成交量: {volume_multiplier:.1f}x 1H均值 ({current_volume:,.2f})
- MA30: ${ma_value:,.2f} ({position})
- 1H参考价: ${reference_price:,.2f}

⏰ {timestamp}"""

        # Lark webhook payload
        payload = {
            "msg_type": "text",
            "content": {
                "text": content
            }
        }

        return payload

    async def send_alert(
        self,
        alert_type: str,
        exchange: str,
        market: str,
        current_price: float,
        ma_value: float,
        volume_multiplier: float,
        current_volume: float,
        reference_price: float
    ) -> bool:
        """Send alert to Lark webhook.

        Args:
            alert_type: Alert type
            exchange: Exchange name
            market: Market symbol
            current_price: Current price
            ma_value: MA30 value
            volume_multiplier: Volume surge multiplier
            current_volume: Current volume
            reference_price: Reference high/low price

        Returns:
            True if message sent successfully
        """
        market_key = f"{exchange}:{market}"

        # Check cooldown
        if self.is_in_cooldown(market_key):
            logger.info(
                "alert_skipped_cooldown",
                market=market_key,
                cooldown_remaining=self.cooldown_seconds - (time.time() - self._last_alert_time[market_key])
            )
            return False

        # Check rate limit
        if self.is_rate_limited():
            logger.warning(
                "alert_rate_limited",
                rate_limit=self.rate_limit
            )
            return False

        # Calculate price change
        if alert_type == AlertType.BULLISH:
            price_change_pct = ((current_price - reference_price) / reference_price) * 100
        else:
            price_change_pct = ((current_price - reference_price) / reference_price) * 100

        # Format message
        payload = self._format_lark_message(
            alert_type=alert_type,
            exchange=exchange,
            market=market,
            current_price=current_price,
            ma_value=ma_value,
            volume_multiplier=volume_multiplier,
            current_volume=current_volume,
            reference_price=reference_price,
            price_change_pct=price_change_pct
        )

        # Send to Lark
        try:
            if not self._http_client:
                raise RuntimeError("HTTP client not initialized. Use async context manager.")

            response = await self._http_client.post(
                self.lark_webhook,
                json=payload
            )
            response.raise_for_status()

            # Update tracking
            self._last_alert_time[market_key] = time.time()
            self._recent_alerts.append(time.time())

            logger.info(
                "alert_sent",
                market=market_key,
                alert_type=alert_type,
                price=current_price,
                volume_multiplier=volume_multiplier
            )

            return True

        except httpx.HTTPError as e:
            logger.error(
                "alert_send_failed",
                market=market_key,
                error=str(e)
            )
            return False
        except Exception as e:
            logger.error(
                "alert_unexpected_error",
                market=market_key,
                error=str(e)
            )
            return False
