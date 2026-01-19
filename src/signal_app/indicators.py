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

        If the bar has the same timestamp as the last bar, update it.
        Otherwise, append as a new bar.

        Args:
            bar: OHLCV data
        """
        # Check if this is an update to the last bar (same timestamp)
        if self.bars and self.bars[-1].timestamp == bar.timestamp:
            # Update the last bar
            self.bars[-1] = bar
        else:
            # New bar with different timestamp
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

        # Calculate average volume of previous 3 bars (前3根K线平均值)
        # ACCEPTANCE_CRITERIA.md: avg_volume_1h = sum(volume[-4:-1]) / 3
        prev_volumes = [bar.volume for bar in bars_list[-self.lookback_bars:-1]]
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

        # Get previous 3 bars' highest price (前3根K线最高价)
        # ACCEPTANCE_CRITERIA.md: high_1h = max(high[-4:-1])
        prev_highs = [bar.high for bar in bars_list[-self.lookback_bars:-1]]
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

        # Get previous 3 bars' lowest price (前3根K线最低价)
        # ACCEPTANCE_CRITERIA.md: low_1h = min(low[-4:-1])
        prev_lows = [bar.low for bar in bars_list[-self.lookback_bars:-1]]
        prev_low = min(prev_lows)

        is_new_low = current_close < prev_low

        return is_new_low, prev_low

    def check_new_high_with_threshold(
        self,
        threshold_pct: float = 0.0
    ) -> tuple[bool, Optional[float], Optional[float]]:
        """检查当前价格是否创新高且突破幅度达到阈值。

        Args:
            threshold_pct: 突破幅度阈值（百分比），例如 0.5 表示 0.5%

        Returns:
            Tuple of (is_breakout, prev_high, breakout_pct)
            - is_breakout: 是否同时满足新高和幅度要求
            - prev_high: 前3根K线最高价
            - breakout_pct: 实际突破幅度百分比
        """
        if len(self.bars) < self.lookback_bars:
            return False, None, None

        bars_list = list(self.bars)
        current_close = bars_list[-1].close

        # 获取前3根K线最高价
        prev_highs = [bar.high for bar in bars_list[-self.lookback_bars:-1]]
        prev_high = max(prev_highs)

        # 计算突破幅度百分比
        if prev_high == 0:
            return False, prev_high, None

        breakout_pct = ((current_close - prev_high) / prev_high) * 100

        # 判断是否同时满足：创新高 AND 突破幅度达标
        is_new_high = current_close > prev_high
        is_breakout = is_new_high and (breakout_pct >= threshold_pct)

        return is_breakout, prev_high, breakout_pct

    def check_new_low_with_threshold(
        self,
        threshold_pct: float = 0.0
    ) -> tuple[bool, Optional[float], Optional[float]]:
        """检查当前价格是否创新低且突破幅度达到阈值。

        Args:
            threshold_pct: 突破幅度阈值（百分比），例如 0.5 表示 0.5%

        Returns:
            Tuple of (is_breakout, prev_low, breakout_pct)
            - is_breakout: 是否同时满足新低和幅度要求
            - prev_low: 前3根K线最低价
            - breakout_pct: 实际突破幅度百分比（负值）
        """
        if len(self.bars) < self.lookback_bars:
            return False, None, None

        bars_list = list(self.bars)
        current_close = bars_list[-1].close

        # 获取前3根K线最低价
        prev_lows = [bar.low for bar in bars_list[-self.lookback_bars:-1]]
        prev_low = min(prev_lows)

        # 计算突破幅度百分比（看跌为负值）
        if prev_low == 0:
            return False, prev_low, None

        breakout_pct = ((current_close - prev_low) / prev_low) * 100

        # 判断是否同时满足：创新低 AND 突破幅度达标
        # 注意：看跌时 breakout_pct 为负值，threshold_pct 为正值
        is_new_low = current_close < prev_low
        is_breakout = is_new_low and (abs(breakout_pct) >= threshold_pct)

        return is_breakout, prev_low, breakout_pct

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
