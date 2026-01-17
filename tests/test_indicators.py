"""Unit tests for indicators module.

Test coverage for MA30, volume surge, new high/low detection.
Target coverage: > 90%
"""

import pytest
import time
from signal_app.indicators import IndicatorEngine, OHLCV


class TestIndicatorEngine:
    """Test cases for IndicatorEngine."""

    def test_initialization(self):
        """Test engine initialization."""
        engine = IndicatorEngine(
            ma_period=30,
            ma_type="SMA",
            volume_threshold=3.0,
            lookback_bars=4,
            max_bars=100
        )
        assert engine.ma_period == 30
        assert engine.ma_type == "SMA"
        assert engine.volume_threshold == 3.0
        assert engine.lookback_bars == 4
        assert engine.max_bars == 100
        assert engine.bar_count == 0

    def test_add_bar(self):
        """Test adding OHLCV bars."""
        engine = IndicatorEngine(ma_period=3)

        bar = OHLCV(
            timestamp=int(time.time()),
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0
        )

        engine.add_bar(bar)
        assert engine.bar_count == 1
        assert engine.current_price == 102.0
        assert engine.current_volume == 1000.0

    def test_has_sufficient_data(self):
        """Test data sufficiency check."""
        engine = IndicatorEngine(ma_period=3)

        # Insufficient data
        assert not engine.has_sufficient_data()

        # Add bars
        for i in range(3):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0 + i,
                volume=1000.0
            )
            engine.add_bar(bar)

        # Now sufficient
        assert engine.has_sufficient_data()

    def test_sma_calculation(self):
        """Test SMA calculation (TC-F02-01)."""
        engine = IndicatorEngine(ma_period=3, ma_type="SMA")

        # Add 3 bars with closes: 100, 102, 104
        closes = [100.0, 102.0, 104.0]
        for i, close in enumerate(closes):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=close,
                high=close + 5,
                low=close - 5,
                close=close,
                volume=1000.0
            )
            engine.add_bar(bar)

        # MA should be (100 + 102 + 104) / 3 = 102
        ma = engine.calculate_ma()
        assert ma is not None
        assert abs(ma - 102.0) < 0.01

    def test_ema_calculation(self):
        """Test EMA calculation."""
        engine = IndicatorEngine(ma_period=3, ma_type="EMA")

        # Add bars
        for i in range(5):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0 + i,
                high=105.0 + i,
                low=95.0 + i,
                close=100.0 + i,
                volume=1000.0
            )
            engine.add_bar(bar)

        # EMA should be calculated
        ema = engine.calculate_ma()
        assert ema is not None
        assert 100.0 < ema < 105.0  # Should be within range

    def test_ma_insufficient_data(self):
        """Test MA returns None when insufficient data."""
        engine = IndicatorEngine(ma_period=30)

        # Add only 10 bars
        for i in range(10):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0
            )
            engine.add_bar(bar)

        # Should return None
        ma = engine.calculate_ma()
        assert ma is None

    def test_volume_surge_detection(self):
        """Test volume surge detection (TC-F02-02)."""
        engine = IndicatorEngine(
            ma_period=3,
            volume_threshold=3.0,
            lookback_bars=4
        )

        # Add 4 bars: [1000, 1000, 1000, 4000]
        volumes = [1000.0, 1000.0, 1000.0, 4000.0]
        for i, volume in enumerate(volumes):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=volume
            )
            engine.add_bar(bar)

        # Check surge
        is_surge, multiplier = engine.check_volume_surge()

        # avg = (1000 + 1000 + 1000) / 3 = 1000
        # current = 4000
        # multiplier = 4000 / 1000 = 4.0 >= 3.0
        assert is_surge is True
        assert multiplier is not None
        assert abs(multiplier - 4.0) < 0.01

    def test_volume_surge_no_surge(self):
        """Test volume surge when not surging."""
        engine = IndicatorEngine(volume_threshold=3.0, lookback_bars=4)

        # Add bars with consistent volume
        for i in range(5):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0
            )
            engine.add_bar(bar)

        is_surge, multiplier = engine.check_volume_surge()
        assert is_surge is False

    def test_volume_surge_insufficient_data(self):
        """Test volume surge with insufficient bars."""
        engine = IndicatorEngine(lookback_bars=4)

        # Add only 2 bars
        for i in range(2):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0
            )
            engine.add_bar(bar)

        is_surge, multiplier = engine.check_volume_surge()
        assert is_surge is False
        assert multiplier is None

    def test_new_high_detection(self):
        """Test new high detection (TC-F02-03)."""
        engine = IndicatorEngine(ma_period=3, lookback_bars=4)

        # Add bars: highs = [100, 101, 102, 105]
        # Current close = 106, MA30 = 100
        highs = [100.0, 101.0, 102.0, 105.0]
        for i, high in enumerate(highs):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=high - 5,
                high=high,
                low=high - 10,
                close=high - 2,
                volume=1000.0
            )
            engine.add_bar(bar)

        # Add breakout bar
        bar = OHLCV(
            timestamp=int(time.time()) + 4,
            open=105.0,
            high=110.0,
            low=104.0,
            close=106.0,  # Higher than prev high 105
            volume=1000.0
        )
        engine.add_bar(bar)

        is_new_high, prev_high = engine.check_new_high()
        assert is_new_high is True
        assert prev_high == 105.0

    def test_new_low_detection(self):
        """Test new low detection."""
        engine = IndicatorEngine(ma_period=3, lookback_bars=4)

        # Add bars: lows = [100, 99, 98, 97]
        lows = [100.0, 99.0, 98.0, 97.0]
        for i, low in enumerate(lows):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=low + 10,
                high=low + 15,
                low=low,
                close=low + 5,
                volume=1000.0
            )
            engine.add_bar(bar)

        # Add breakdown bar
        bar = OHLCV(
            timestamp=int(time.time()) + 4,
            open=96.0,
            high=98.0,
            low=94.0,
            close=95.0,  # Lower than prev low 97
            volume=1000.0
        )
        engine.add_bar(bar)

        is_new_low, prev_low = engine.check_new_low()
        assert is_new_low is True
        assert prev_low == 97.0

    def test_no_new_high_when_not_breaking(self):
        """Test no new high when price doesn't break."""
        engine = IndicatorEngine(lookback_bars=4)

        # Add bars with consistent highs
        for i in range(5):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0
            )
            engine.add_bar(bar)

        is_new_high, _ = engine.check_new_high()
        assert is_new_high is False

    def test_sliding_window_max_bars(self):
        """Test sliding window enforces max_bars limit."""
        engine = IndicatorEngine(ma_period=3, max_bars=10)

        # Add 20 bars
        for i in range(20):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0 + i,
                high=105.0 + i,
                low=95.0 + i,
                close=102.0 + i,
                volume=1000.0
            )
            engine.add_bar(bar)

        # Should only keep last 10 bars
        assert engine.bar_count == 10
        # First bar should be bar #10 (close = 112.0)
        assert engine.bars[0].close == 112.0

    def test_zero_volume_handling(self):
        """Test handling of zero average volume."""
        engine = IndicatorEngine(volume_threshold=3.0, lookback_bars=4)

        # Add bars with zero volume
        for i in range(5):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=0.0
            )
            engine.add_bar(bar)

        is_surge, multiplier = engine.check_volume_surge()
        assert is_surge is False
        assert multiplier is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
