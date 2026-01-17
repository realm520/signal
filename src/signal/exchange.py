"""Exchange WebSocket subscription layer."""

import asyncio
from typing import Callable, Dict, Optional
import ccxt.pro as ccxtpro
import structlog

from .indicators import OHLCV

logger = structlog.get_logger()


class ExchangeMonitor:
    """Monitor exchange markets via WebSocket."""

    def __init__(
        self,
        exchange_name: str,
        markets: list[str],
        timeframe: str = "15m",
        max_retries: int = 5,
        retry_delay: int = 5
    ):
        """Initialize exchange monitor.

        Args:
            exchange_name: Exchange name (e.g., 'binance')
            markets: List of market symbols (e.g., ['BTC/USDT', 'ETH/USDT'])
            timeframe: Timeframe for OHLCV data
            max_retries: Maximum reconnection attempts
            retry_delay: Delay between retries in seconds
        """
        self.exchange_name = exchange_name
        self.markets = markets
        self.timeframe = timeframe
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize exchange
        exchange_class = getattr(ccxtpro, exchange_name)
        self.exchange = exchange_class({
            'enableRateLimit': True,
        })

        # Callback for OHLCV data
        self._callback: Optional[Callable] = None

        # Running state
        self._running = False
        self._tasks: list[asyncio.Task] = []

    def set_callback(self, callback: Callable) -> None:
        """Set callback for OHLCV updates.

        Args:
            callback: Async function(exchange, market, ohlcv) to call
        """
        self._callback = callback

    async def _watch_ohlcv(self, market: str) -> None:
        """Watch OHLCV data for a market.

        Args:
            market: Market symbol
        """
        retries = 0

        while self._running and retries < self.max_retries:
            try:
                logger.info(
                    "watching_market",
                    exchange=self.exchange_name,
                    market=market,
                    timeframe=self.timeframe
                )

                while self._running:
                    try:
                        # Watch OHLCV updates
                        ohlcvs = await self.exchange.watch_ohlcv(
                            market,
                            timeframe=self.timeframe
                        )

                        # Get latest OHLCV
                        if ohlcvs and len(ohlcvs) > 0:
                            latest = ohlcvs[-1]

                            # Convert to OHLCV dataclass
                            ohlcv = OHLCV(
                                timestamp=latest[0],
                                open=float(latest[1]),
                                high=float(latest[2]),
                                low=float(latest[3]),
                                close=float(latest[4]),
                                volume=float(latest[5])
                            )

                            # Call callback
                            if self._callback:
                                await self._callback(
                                    self.exchange_name,
                                    market,
                                    ohlcv
                                )

                        # Reset retry counter on success
                        retries = 0

                    except ccxtpro.NetworkError as e:
                        logger.warning(
                            "network_error",
                            exchange=self.exchange_name,
                            market=market,
                            error=str(e)
                        )
                        # Network error, will retry
                        break

                    except Exception as e:
                        logger.error(
                            "watch_error",
                            exchange=self.exchange_name,
                            market=market,
                            error=str(e)
                        )
                        # Other errors, will retry
                        break

            except Exception as e:
                logger.error(
                    "connection_error",
                    exchange=self.exchange_name,
                    market=market,
                    error=str(e)
                )

            # Retry with exponential backoff
            if self._running and retries < self.max_retries:
                retries += 1
                delay = self.retry_delay * (2 ** (retries - 1))
                logger.info(
                    "reconnecting",
                    exchange=self.exchange_name,
                    market=market,
                    retry=retries,
                    delay=delay
                )
                await asyncio.sleep(delay)

        if retries >= self.max_retries:
            logger.error(
                "max_retries_exceeded",
                exchange=self.exchange_name,
                market=market
            )

    async def start(self) -> None:
        """Start monitoring all markets."""
        if self._running:
            logger.warning("monitor_already_running", exchange=self.exchange_name)
            return

        self._running = True

        logger.info(
            "starting_monitor",
            exchange=self.exchange_name,
            markets=self.markets
        )

        # Create tasks for each market
        for market in self.markets:
            task = asyncio.create_task(self._watch_ohlcv(market))
            self._tasks.append(task)

        logger.info(
            "monitor_started",
            exchange=self.exchange_name,
            market_count=len(self.markets)
        )

    async def stop(self) -> None:
        """Stop monitoring."""
        if not self._running:
            return

        logger.info("stopping_monitor", exchange=self.exchange_name)

        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # Close exchange connection
        await self.exchange.close()

        self._tasks.clear()

        logger.info("monitor_stopped", exchange=self.exchange_name)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
