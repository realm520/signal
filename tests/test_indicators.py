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

    def test_check_new_high_with_threshold_basic(self):
        """测试基础突破幅度检测（看涨）。"""
        engine = IndicatorEngine(ma_period=3, lookback_bars=4)

        # 添加3根K线：前3根最高价为100
        for i in range(3):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=95.0,
                high=100.0,
                low=90.0,
                close=98.0,
                volume=1000.0
            )
            engine.add_bar(bar)

        # 当前K线：收盘价103（突破3%）
        bar = OHLCV(
            timestamp=int(time.time()) + 3,
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,  # (103-100)/100 = 3%
            volume=1000.0
        )
        engine.add_bar(bar)

        # 测试：0.5% 阈值应该通过
        is_breakout, prev_high, breakout_pct = engine.check_new_high_with_threshold(0.5)
        assert is_breakout is True
        assert prev_high == 100.0
        assert abs(breakout_pct - 3.0) < 0.01

        # 测试：5% 阈值应该不通过
        is_breakout, _, _ = engine.check_new_high_with_threshold(5.0)
        assert is_breakout is False

    def test_check_new_low_with_threshold_basic(self):
        """测试基础突破幅度检测（看跌）。"""
        engine = IndicatorEngine(ma_period=3, lookback_bars=4)

        # 添加3根K线：前3根最低价为100
        for i in range(3):
            bar = OHLCV(
                timestamp=int(time.time()) + i,
                open=105.0,
                high=110.0,
                low=100.0,
                close=102.0,
                volume=1000.0
            )
            engine.add_bar(bar)

        # 当前K线：收盘价97（下跌3%）
        bar = OHLCV(
            timestamp=int(time.time()) + 3,
            open=100.0,
            high=101.0,
            low=95.0,
            close=97.0,  # (97-100)/100 = -3%
            volume=1000.0
        )
        engine.add_bar(bar)

        # 测试：0.5% 阈值应该通过
        is_breakout, prev_low, breakout_pct = engine.check_new_low_with_threshold(0.5)
        assert is_breakout is True
        assert prev_low == 100.0
        assert abs(breakout_pct - (-3.0)) < 0.01

        # 测试：5% 阈值应该不通过
        is_breakout, _, _ = engine.check_new_low_with_threshold(5.0)
        assert is_breakout is False

    def test_breakout_threshold_exactly_at_boundary(self):
        """测试突破幅度刚好等于阈值的边界情况。"""
        engine = IndicatorEngine(lookback_bars=4)

        # 前3根K线最高价为100
        for i in range(3):
            engine.add_bar(OHLCV(
                timestamp=int(time.time()) + i,
                open=95.0, high=100.0, low=90.0, close=98.0, volume=1000.0
            ))

        # 当前收盘价刚好为102（突破2%）
        engine.add_bar(OHLCV(
            timestamp=int(time.time()) + 3,
            open=100.0, high=103.0, low=99.0, close=102.0, volume=1000.0
        ))

        # 2% 阈值应该通过（大于等于）
        is_breakout, _, breakout_pct = engine.check_new_high_with_threshold(2.0)
        assert is_breakout is True
        assert abs(breakout_pct - 2.0) < 0.01

    def test_breakout_threshold_insufficient_data(self):
        """测试数据不足时的行为。"""
        engine = IndicatorEngine(lookback_bars=4)

        # 仅添加2根K线（不足4根）
        for i in range(2):
            engine.add_bar(OHLCV(
                timestamp=int(time.time()) + i,
                open=100.0, high=105.0, low=95.0, close=102.0, volume=1000.0
            ))

        is_breakout, prev_high, breakout_pct = engine.check_new_high_with_threshold(0.5)
        assert is_breakout is False
        assert prev_high is None
        assert breakout_pct is None

    def test_breakout_threshold_zero_price_protection(self):
        """测试零价格保护（防止除零错误）。"""
        engine = IndicatorEngine(lookback_bars=4)

        # 添加3根价格为0的异常K线
        for i in range(3):
            engine.add_bar(OHLCV(
                timestamp=int(time.time()) + i,
                open=0.0, high=0.0, low=0.0, close=0.0, volume=1000.0
            ))

        engine.add_bar(OHLCV(
            timestamp=int(time.time()) + 3,
            open=100.0, high=105.0, low=95.0, close=102.0, volume=1000.0
        ))

        # 应该安全返回 False
        is_breakout, prev_high, breakout_pct = engine.check_new_high_with_threshold(0.5)
        assert is_breakout is False
        assert prev_high == 0.0
        assert breakout_pct is None

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

    def test_same_timestamp_bar_update(self):
        """测试同一timestamp的K线应该更新而不是追加（修复WebSocket重复推送bug）。"""
        engine = IndicatorEngine(ma_period=3, lookback_bars=4)

        # 模拟同一根15分钟K线的多次WebSocket更新
        timestamp = int(time.time())

        # 第一次推送（8:00:00）：K线刚开始，成交量很小
        bar1 = OHLCV(
            timestamp=timestamp,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0
        )
        engine.add_bar(bar1)
        assert engine.bar_count == 1
        assert engine.current_volume == 1000.0

        # 第二次推送（8:00:22）：同一根K线，成交量增加
        bar2 = OHLCV(
            timestamp=timestamp,  # 相同的timestamp
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=5000.0  # 成交量增加
        )
        engine.add_bar(bar2)

        # 关键断言：应该只有1根K线（更新），而不是2根（追加）
        assert engine.bar_count == 1
        assert engine.current_price == 101.0
        assert engine.current_volume == 5000.0

        # 第三次推送（8:00:32）：同一根K线，价格和成交量继续变化
        bar3 = OHLCV(
            timestamp=timestamp,  # 相同的timestamp
            open=100.0,
            high=103.0,
            low=98.0,
            close=102.0,
            volume=8000.0
        )
        engine.add_bar(bar3)

        # 仍然应该只有1根K线
        assert engine.bar_count == 1
        assert engine.current_price == 102.0
        assert engine.current_volume == 8000.0

    def test_different_timestamp_bar_append(self):
        """测试不同timestamp的K线应该追加为新K线。"""
        engine = IndicatorEngine(ma_period=3, lookback_bars=4)

        # 添加3根不同时间的K线
        for i in range(3):
            bar = OHLCV(
                timestamp=int(time.time()) + i * 900,  # 每根K线间隔15分钟
                open=100.0 + i,
                high=105.0 + i,
                low=95.0 + i,
                close=102.0 + i,
                volume=1000.0 + i * 100
            )
            engine.add_bar(bar)

        # 应该有3根不同的K线
        assert engine.bar_count == 3
        assert engine.bars[0].close == 102.0
        assert engine.bars[1].close == 103.0
        assert engine.bars[2].close == 104.0

    def test_volume_surge_with_correct_bar_count(self):
        """测试修复后，成交量突破计算应该使用真正的前3根K线（回归测试ZEN bug）。"""
        engine = IndicatorEngine(
            ma_period=3,
            volume_threshold=3.0,
            lookback_bars=4
        )

        base_time = int(time.time())

        # 添加3根历史K线，成交量都是1000
        for i in range(3):
            bar = OHLCV(
                timestamp=base_time + i * 900,  # 不同时间戳
                open=11.0,
                high=11.5,
                low=10.5,
                close=11.2,
                volume=1000.0
            )
            engine.add_bar(bar)

        # 第4根K线：模拟WebSocket多次更新
        current_time = base_time + 3 * 900

        # 多次推送同一根K线（模拟WebSocket实时更新）
        for update_volume in [2000.0, 8000.0, 14428.0]:
            bar = OHLCV(
                timestamp=current_time,  # 相同timestamp
                open=11.5,
                high=11.6,
                low=10.5,
                close=10.962,
                volume=update_volume  # 成交量不断累积
            )
            engine.add_bar(bar)

        # 应该只有4根K线，而不是6根（3根历史 + 3次更新 = 6）
        assert engine.bar_count == 4

        # 检查成交量突破：14428 / ((1000+1000+1000)/3) ≈ 14.4倍
        is_surge, multiplier = engine.check_volume_surge()
        assert is_surge is True
        assert multiplier is not None
        assert multiplier > 14.0  # 应该远大于3.0阈值
        assert abs(multiplier - 14.428) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
