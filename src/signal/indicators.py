"""Technical indicators calculation engine."""

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional


@dataclass
class OHLCV:
    """OHLCV data structure."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorEngine:
    """Calculate technical indicators from OHLCV data."""

    def __init__(
        self,
        ma_period: int = 30,
        ma_type: str = "SMA",
        volume_threshold: float = 3.0,
        lookback_bars: int = 4,
        max_bars: int = 100
    ):
        """Initialize indicator engine.

        Args:
            ma_period: Moving average period
            ma_type: Moving average type (SMA or EMA)
            volume_threshold: Volume surge threshold multiplier
            lookback_bars: Number of bars to look back for high/low
            max_bars: Maximum bars to keep in memory
        """
        self.ma_period = ma_period
        self.ma_type = ma_type
        self.volume_threshold = volume_threshold
        self.lookback_bars = lookback_bars
        self.max_bars = max_bars

        # Store OHLCV data
        self.bars: Deque[OHLCV] = deque(maxlen=max_bars)

    def add_bar(self, bar: OHLCV) -> None:
        """Add new OHLCV bar to history.

        Args:
            bar: OHLCV data
        """
        self.bars.append(bar)

    def has_sufficient_data(self) -> bool:
        """Check if we have enough data for calculations.

        Returns:
            True if we have at least ma_period bars
        """
        return len(self.bars) >= self.ma_period

    def calculate_ma(self) -> Optional[float]:
        """Calculate moving average.

        Returns:
            MA value or None if insufficient data
        """
        if not self.has_sufficient_data():
            return None

        closes = [bar.close for bar in list(self.bars)[-self.ma_period:]]

        if self.ma_type == "SMA":
            return sum(closes) / len(closes)
        elif self.ma_type == "EMA":
            # EMA calculation
            multiplier = 2 / (self.ma_period + 1)
            ema = closes[0]
            for close in closes[1:]:
                ema = (close - ema) * multiplier + ema
            return ema
        else:
            raise ValueError(f"Unknown MA type: {self.ma_type}")

    def check_volume_surge(self) -> tuple[bool, Optional[float]]:
        """Check if current volume is surging.

        Returns:
            Tuple of (is_surge, volume_multiplier)
        """
        if len(self.bars) < self.lookback_bars:
            return False, None

        bars_list = list(self.bars)
        current_volume = bars_list[-1].volume

        # Calculate average volume of previous bars (excluding current)
        prev_volumes = [bar.volume for bar in bars_list[-(self.lookback_bars + 1):-1]]
        avg_volume = sum(prev_volumes) / len(prev_volumes)

        if avg_volume == 0:
            return False, None

        volume_multiplier = current_volume / avg_volume
        is_surge = volume_multiplier >= self.volume_threshold

        return is_surge, volume_multiplier

    def check_new_high(self) -> tuple[bool, Optional[float]]:
        """Check if current price is a new high.

        Returns:
            Tuple of (is_new_high, high_price)
        """
        if len(self.bars) < self.lookback_bars:
            return False, None

        bars_list = list(self.bars)
        current_close = bars_list[-1].close

        # Get previous bars' highest price (excluding current)
        prev_highs = [bar.high for bar in bars_list[-(self.lookback_bars + 1):-1]]
        prev_high = max(prev_highs)

        is_new_high = current_close > prev_high

        return is_new_high, prev_high

    def check_new_low(self) -> tuple[bool, Optional[float]]:
        """Check if current price is a new low.

        Returns:
            Tuple of (is_new_low, low_price)
        """
        if len(self.bars) < self.lookback_bars:
            return False, None

        bars_list = list(self.bars)
        current_close = bars_list[-1].close

        # Get previous bars' lowest price (excluding current)
        prev_lows = [bar.low for bar in bars_list[-(self.lookback_bars + 1):-1]]
        prev_low = min(prev_lows)

        is_new_low = current_close < prev_low

        return is_new_low, prev_low

    @property
    def current_price(self) -> Optional[float]:
        """Get current close price."""
        if not self.bars:
            return None
        return self.bars[-1].close

    @property
    def current_volume(self) -> Optional[float]:
        """Get current volume."""
        if not self.bars:
            return None
        return self.bars[-1].volume

    @property
    def bar_count(self) -> int:
        """Get number of bars in memory."""
        return len(self.bars)
