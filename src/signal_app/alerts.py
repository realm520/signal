"""Alert condition checking and Lark notification module."""

import time
from datetime import datetime, timezone

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
        mention_user_id: str | None = None,
    ) -> None:
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

        self._last_alert_time: dict[str, float] = {}
        self._recent_alerts: list[float] = []
        self._http_client: httpx.AsyncClient | None = None
        self._startup_timestamp_ms: int = int(time.time() * 1000)

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
        is_breakout_high: bool | None = None,
        is_breakout_low: bool | None = None,
        breakout_pct_high: float | None = None,
        breakout_pct_low: float | None = None,
    ) -> str | None:
        """Check if alert conditions are met.

        Args:
            exchange: Exchange name
            market: Market symbol
            current_price: Current price
            ma_value: MA30 value
            volume_surge: Whether volume surge detected
            volume_multiplier: Volume multiplier value
            is_new_high: Whether price is at 1-hour high
            is_new_low: Whether price is at 1-hour low
            is_breakout_high: Enhanced bullish breakout detection (optional)
            is_breakout_low: Enhanced bearish breakout detection (optional)
            breakout_pct_high: Bullish breakout percentage (for logging)
            breakout_pct_low: Bearish breakout percentage (for logging)

        Returns:
            Alert type (bullish/bearish) or None
        """
        if not volume_surge:
            return None

        # Use enhanced detection if provided, otherwise fall back to basic detection
        bullish_breakout = is_breakout_high if is_breakout_high is not None else is_new_high
        bearish_breakout = is_breakout_low if is_breakout_low is not None else is_new_low

        if current_price > ma_value and bullish_breakout:
            return AlertType.BULLISH

        if current_price < ma_value and bearish_breakout:
            return AlertType.BEARISH

        return None

    def is_in_cooldown(self, market_key: str) -> bool:
        """Check if market is in cooldown period.

        Args:
            market_key: Market identifier (e.g., "binance:BTC/USDT")

        Returns:
            True if in cooldown period
        """
        last_alert = self._last_alert_time.get(market_key)
        if last_alert is None:
            return False

        elapsed = time.time() - last_alert
        return elapsed < self.cooldown_seconds

    def is_rate_limited(self) -> bool:
        """Check if rate limit is exceeded.

        Returns:
            True if rate limit exceeded
        """
        current_time = time.time()
        self._recent_alerts = [t for t in self._recent_alerts if current_time - t < 60]
        return len(self._recent_alerts) >= self.rate_limit

    def _is_lark_id(self, user_id: str) -> bool:
        """Check if user_id is a valid Lark ID format.

        Args:
            user_id: User identifier to check

        Returns:
            True if it's an open_id or user_id format
        """
        if user_id.startswith("ou_"):
            return True

        is_user_id = (
            8 <= len(user_id) <= 12
            and user_id.isalnum()
            and user_id.islower()
        )
        return is_user_id

    def _format_mention_prefix(self) -> str:
        """Format mention prefix for Lark message.

        Returns:
            Mention prefix string or empty string
        """
        if not self.mention_user_id:
            return ""

        if self._is_lark_id(self.mention_user_id):
            return f'<at user_id="{self.mention_user_id}"></at> '

        return f"@{self.mention_user_id} "

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
        breakout_pct: float | None = None,
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
            breakout_pct: Breakout percentage (optional)

        Returns:
            Lark message payload
        """
        if alert_type == AlertType.BULLISH:
            emoji, signal, direction, position = "🚀", "向上插针", "↑", "上方"
        else:
            emoji, signal, direction, position = "📉", "向下插针", "↓", "下方"

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        breakout_info = f"\n- 突破幅度: {abs(breakout_pct):.2f}%" if breakout_pct is not None else ""
        mention_prefix = self._format_mention_prefix()

        content = f"""{mention_prefix}{emoji} **{signal}** | {exchange.capitalize()}
📊 **{market}**: ${current_price:,.2f} {direction} {price_change_pct:+.2f}%

📈 **指标**:
- 成交量: {volume_multiplier:.1f}x 1H均值 ({current_volume:,.2f})
- MA30: ${ma_value:,.2f} ({position})
- 1H参考价: ${reference_price:,.2f}{breakout_info}

⏰ {timestamp}"""

        return {"msg_type": "text", "content": {"text": content}}

    async def _send_lark_message(self, payload: dict, log_event: str, **log_kwargs) -> bool:
        """Send message to Lark webhook.

        Args:
            payload: Message payload
            log_event: Event name for success logging
            **log_kwargs: Additional logging context

        Returns:
            True if message sent successfully
        """
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized. Use async context manager.")

        try:
            response = await self._http_client.post(self.lark_webhook, json=payload)
            response.raise_for_status()
            logger.info(log_event, **log_kwargs)
            return True

        except httpx.HTTPError as e:
            logger.error(f"{log_event}_failed", error=str(e), **log_kwargs)
            return False

        except Exception as e:
            logger.error(f"{log_event}_unexpected_error", error=str(e), **log_kwargs)
            return False

    async def send_startup_notification(
        self,
        exchanges: list[str],
        markets_count: int,
    ) -> bool:
        """Send startup notification message.

        Args:
            exchanges: List of exchange names
            markets_count: Number of markets being monitored

        Returns:
            True if message sent successfully
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        mention_prefix = self._format_mention_prefix()
        exchanges_str = ", ".join(exchanges)

        content = f"""{mention_prefix}🚀 **Signal 系统启动**

✅ **状态**: 监控服务已启动
📊 **交易所**: {exchanges_str}
📈 **市场数**: {markets_count} 个
⏰ **启动时间**: {timestamp}

系统正在实时监控市场，满足条件时会推送告警。"""

        payload = {"msg_type": "text", "content": {"text": content}}
        return await self._send_lark_message(payload, "startup_notification_sent")

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
        breakout_pct: float | None = None,
        bar_timestamp_ms: int | None = None,
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
            breakout_pct: Breakout percentage (optional)
            bar_timestamp_ms: K-line timestamp in milliseconds (optional)

        Returns:
            True if message sent successfully
        """
        market_key = f"{exchange}:{market}"

        # Startup protection: skip alerts for historical data
        if bar_timestamp_ms is not None and bar_timestamp_ms < self._startup_timestamp_ms:
            logger.debug(
                "alert_skipped_historical",
                market=market_key,
                bar_timestamp=bar_timestamp_ms,
                startup_timestamp=self._startup_timestamp_ms,
            )
            return False

        if self.is_in_cooldown(market_key):
            cooldown_remaining = self.cooldown_seconds - (time.time() - self._last_alert_time[market_key])
            logger.info("alert_skipped_cooldown", market=market_key, cooldown_remaining=cooldown_remaining)
            return False

        if self.is_rate_limited():
            logger.warning("alert_rate_limited", rate_limit=self.rate_limit)
            return False

        price_change_pct = ((current_price - reference_price) / reference_price) * 100

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
            breakout_pct=breakout_pct,
        )

        success = await self._send_lark_message(
            payload,
            "alert_sent",
            market=market_key,
            alert_type=alert_type,
            price=current_price,
            volume_multiplier=volume_multiplier,
        )

        if success:
            current_time = time.time()
            self._last_alert_time[market_key] = current_time
            self._recent_alerts.append(current_time)

        return success
