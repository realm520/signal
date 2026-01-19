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
        rate_limit: int = 10,
        mention_user_id: Optional[str] = None
    ):
        """Initialize alert manager.

        Args:
            lark_webhook: Lark webhook URL
            cooldown_seconds: Cooldown period in seconds
            rate_limit: Maximum messages per minute
            mention_user_id: Lark user open_id to mention (optional)
        """
        self.lark_webhook = lark_webhook
        self.cooldown_seconds = cooldown_seconds
        self.rate_limit = rate_limit
        self.mention_user_id = mention_user_id

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
        is_new_low: bool,
        # 新增可选参数
        is_breakout_high: Optional[bool] = None,
        is_breakout_low: Optional[bool] = None,
        breakout_pct_high: Optional[float] = None,
        breakout_pct_low: Optional[float] = None
    ) -> Optional[str]:
        """检查告警条件是否满足。

        新增参数:
            is_breakout_high: 是否满足看涨突破幅度（可选）
            is_breakout_low: 是否满足看跌突破幅度（可选）
            breakout_pct_high: 实际看涨突破幅度（可选，用于日志）
            breakout_pct_low: 实际看跌突破幅度（可选，用于日志）

        Returns:
            Alert type (bullish/bearish) or None
        """
        # 条件1：成交量放大（必需）
        if not volume_surge:
            return None

        # 条件2a：看涨信号
        # 优先使用增强型检测（如果提供）
        use_enhanced_bullish = is_breakout_high is not None
        bullish_condition = (
            is_breakout_high if use_enhanced_bullish else is_new_high
        )

        if current_price > ma_value and bullish_condition:
            return AlertType.BULLISH

        # 条件2b：看跌信号
        use_enhanced_bearish = is_breakout_low is not None
        bearish_condition = (
            is_breakout_low if use_enhanced_bearish else is_new_low
        )

        if current_price < ma_value and bearish_condition:
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
        price_change_pct: float,
        # 新增参数（可选）
        breakout_pct: Optional[float] = None
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
            breakout_pct: 突破幅度百分比（可选）

        Returns:
            Lark message payload
        """
        # Determine emoji and signal name
        if alert_type == AlertType.BULLISH:
            emoji = "🚀"
            signal = "向上插针"
            direction = "↑"
            position = "上方"
        else:
            emoji = "📉"
            signal = "向下插针"
            direction = "↓"
            position = "下方"

        # Format timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 新增：突破幅度显示
        breakout_info = ""
        if breakout_pct is not None:
            breakout_info = f"\n- 突破幅度: {abs(breakout_pct):.2f}%"

        # Build message content with @ mention if configured
        mention_prefix = ""
        if self.mention_user_id:
            # 检查是否是简单的用户名（不是 open_id）
            if self.mention_user_id.startswith('ou_'):
                # 使用 open_id 实现真正的 @ 通知
                mention_prefix = f"<at user_id=\"{self.mention_user_id}\"></at> "
            else:
                # 使用用户名，只是文本显示（无通知）
                mention_prefix = f"@{self.mention_user_id} "

        content = f"""{mention_prefix}{emoji} **{signal}** | {exchange.capitalize()}
📊 **{market}**: ${current_price:,.2f} {direction} {price_change_pct:+.2f}%

📈 **指标**:
- 成交量: {volume_multiplier:.1f}x 1H均值 ({current_volume:,.2f})
- MA30: ${ma_value:,.2f} ({position})
- 1H参考价: ${reference_price:,.2f}{breakout_info}

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
        reference_price: float,
        # 新增参数（可选）
        breakout_pct: Optional[float] = None
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
            breakout_pct: 突破幅度百分比（可选）

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
            price_change_pct=price_change_pct,
            # 新增参数（可选）
            breakout_pct=breakout_pct
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
