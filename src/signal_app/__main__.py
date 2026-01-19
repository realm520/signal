"""Main program entry point."""

import asyncio
import signal
import sys
from typing import Dict

import structlog

from .config import Config
from .exchange import ExchangeMonitor
from .indicators import IndicatorEngine, OHLCV
from .alerts import AlertManager
from .utils import setup_logging

logger = structlog.get_logger()


class SignalApp:
    """Main application coordinator."""

    def __init__(self, config: Config):
        """Initialize application.

        Args:
            config: Configuration object
        """
        self.config = config

        # Indicator engines for each market
        self.indicators: Dict[str, IndicatorEngine] = {}

        # Exchange monitors
        self.monitors: list[ExchangeMonitor] = []

        # Alert manager
        self.alert_manager: AlertManager | None = None

        # Running state
        self._running = False

    async def _on_ohlcv_update(
        self,
        exchange: str,
        market: str,
        ohlcv: OHLCV
    ) -> None:
        """Handle OHLCV update from exchange.

        Args:
            exchange: Exchange name
            market: Market symbol
            ohlcv: OHLCV data
        """
        market_key = f"{exchange}:{market}"

        # Get or create indicator engine
        if market_key not in self.indicators:
            self.indicators[market_key] = IndicatorEngine(
                ma_period=self.config.ma_period,
                ma_type=self.config.ma_type,
                volume_threshold=self.config.volume_threshold,
                lookback_bars=self.config.lookback_bars
            )

        engine = self.indicators[market_key]

        # Add new bar
        engine.add_bar(ohlcv)

        logger.debug(
            "ohlcv_update",
            market=market_key,
            close=ohlcv.close,
            volume=ohlcv.volume,
            bar_count=engine.bar_count
        )

        # Check if we have sufficient data
        if not engine.has_sufficient_data():
            logger.debug(
                "insufficient_data",
                market=market_key,
                current=engine.bar_count,
                required=self.config.ma_period
            )
            return

        # Calculate indicators
        ma_value = engine.calculate_ma()
        volume_surge, volume_multiplier = engine.check_volume_surge()

        # 获取突破幅度阈值
        breakout_threshold = self.config.breakout_threshold_pct

        # 使用增强型检测
        is_breakout_high, prev_high, breakout_pct_high = \
            engine.check_new_high_with_threshold(breakout_threshold)
        is_breakout_low, prev_low, breakout_pct_low = \
            engine.check_new_low_with_threshold(breakout_threshold)

        # 仍然计算原有的 is_new_high/is_new_low（用于日志对比和调试）
        is_new_high, _ = engine.check_new_high()
        is_new_low, _ = engine.check_new_low()

        current_price = engine.current_price
        current_volume = engine.current_volume

        logger.info(
            "indicators_calculated",
            market=market_key,
            price=current_price,
            ma=ma_value,
            volume_surge=volume_surge,
            volume_mult=volume_multiplier,
            new_high=is_new_high,
            new_low=is_new_low,
            # 新增日志字段
            breakout_high=is_breakout_high,
            breakout_low=is_breakout_low,
            breakout_pct_high=breakout_pct_high,
            breakout_pct_low=breakout_pct_low
        )

        # Check alert conditions
        if not self.alert_manager:
            return

        alert_type = self.alert_manager.check_alert_conditions(
            exchange=exchange,
            market=market,
            current_price=current_price,
            ma_value=ma_value,
            volume_surge=volume_surge,
            volume_multiplier=volume_multiplier or 0,
            is_new_high=is_new_high,
            is_new_low=is_new_low,
            # 新增参数
            is_breakout_high=is_breakout_high,
            is_breakout_low=is_breakout_low,
            breakout_pct_high=breakout_pct_high,
            breakout_pct_low=breakout_pct_low
        )

        if alert_type:
            # 确定参考价格和突破幅度
            if alert_type == "bullish":
                reference_price = prev_high
                breakout_pct = breakout_pct_high
            else:
                reference_price = prev_low
                breakout_pct = breakout_pct_low

            # Send alert (with bar timestamp for startup protection)
            await self.alert_manager.send_alert(
                alert_type=alert_type,
                exchange=exchange,
                market=market,
                current_price=current_price,
                ma_value=ma_value,
                volume_multiplier=volume_multiplier or 0,
                current_volume=current_volume,
                reference_price=reference_price or current_price,
                # 新增参数（可选）
                breakout_pct=breakout_pct,
                bar_timestamp_ms=ohlcv.timestamp
            )

    async def start(self) -> None:
        """Start the application."""
        if self._running:
            logger.warning("app_already_running")
            return

        self._running = True

        logger.info(
            "starting_app",
            exchanges=len(self.config.exchanges),
            ma_period=self.config.ma_period,
            volume_threshold=self.config.volume_threshold
        )

        # Initialize alert manager
        self.alert_manager = AlertManager(
            lark_webhook=self.config.lark_webhook,
            cooldown_seconds=self.config.cooldown_seconds,
            rate_limit=self.config.rate_limit,
            mention_user_id=self.config.mention_user_id
        )
        await self.alert_manager.__aenter__()

        # Create monitors for each exchange
        for exchange_config in self.config.exchanges:
            exchange_name = exchange_config['name']
            markets = exchange_config['markets']

            monitor = ExchangeMonitor(
                exchange_name=exchange_name,
                markets=markets,
                timeframe="15m",
                historical_bars=self.config.historical_bars
            )

            # Set callback
            monitor.set_callback(self._on_ohlcv_update)

            # Start monitoring
            await monitor.start()

            self.monitors.append(monitor)

        logger.info("app_started", monitor_count=len(self.monitors))

        # Send startup notification
        exchanges_list = [ex['name'] for ex in self.config.exchanges]
        total_markets = sum(len(ex['markets']) for ex in self.config.exchanges)
        await self.alert_manager.send_startup_notification(
            exchanges=exchanges_list,
            markets_count=total_markets
        )

    async def stop(self) -> None:
        """Stop the application."""
        if not self._running:
            return

        logger.info("stopping_app")

        self._running = False

        # Stop all monitors
        for monitor in self.monitors:
            await monitor.stop()

        # Close alert manager
        if self.alert_manager:
            await self.alert_manager.__aexit__(None, None, None)

        self.monitors.clear()

        logger.info("app_stopped")

    async def run(self) -> None:
        """Run the application until interrupted."""
        await self.start()

        try:
            # Run forever
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("app_cancelled")
        finally:
            await self.stop()


def signal_handler(sig, frame):
    """Handle interrupt signal."""
    logger.info("interrupt_received", signal=sig)
    sys.exit(0)


async def async_main() -> None:
    """Async main function."""
    try:
        # Load configuration
        logger.info("loading_config")
        config = Config()

        # Setup logging
        setup_logging(
            level=config.log_level,
            log_file=config.log_file
        )

        logger.info("config_loaded")

        # Create and run app
        app = SignalApp(config)

        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        await app.run()

    except FileNotFoundError as e:
        logger.error("config_file_not_found", error=str(e))
        sys.exit(1)
    except ValueError as e:
        logger.error("config_validation_failed", error=str(e))
        sys.exit(1)
    except Exception as e:
        logger.error("unexpected_error", error=str(e), exc_info=True)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
        sys.exit(0)


if __name__ == "__main__":
    main()
