"""Unit tests for config module.

Test coverage for configuration loading and validation.
Target coverage: > 80%
"""

import pytest
import os
import tempfile
from pathlib import Path
from signal_app.config import Config


class TestConfig:
    """Test cases for Config class."""

    def test_load_valid_config(self):
        """Test loading valid configuration (TC-F05-01)."""
        # Create temporary config file
        config_content = """
exchanges:
  - name: binance
    markets:
      - BTC/USDT
      - ETH/USDT
    enabled: true

indicators:
  ma_period: 30
  ma_type: SMA
  volume_threshold: 3.0
  lookback_bars: 4

alerts:
  lark_webhook: "https://example.com/webhook"
  cooldown_seconds: 300
  rate_limit: 10

logging:
  level: INFO
  file: logs/signal.log
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            config = Config(temp_path)
            assert len(config.exchanges) == 1
            assert config.exchanges[0]['name'] == 'binance'
            assert config.ma_period == 30
            assert config.volume_threshold == 3.0
            assert config.lark_webhook == "https://example.com/webhook"
        finally:
            os.unlink(temp_path)

    def test_config_file_not_found(self):
        """Test error when config file doesn't exist (TC-F05-02)."""
        with pytest.raises(FileNotFoundError) as exc_info:
            Config("/nonexistent/path/config.yaml")

        assert "Config file not found" in str(exc_info.value)

    def test_environment_variable_replacement(self):
        """Test environment variable substitution (TC-F05-03)."""
        config_content = """
exchanges:
  - name: binance
    markets:
      - BTC/USDT

indicators:
  ma_period: 30
  volume_threshold: 3.0
  lookback_bars: 4

alerts:
  lark_webhook: "${TEST_WEBHOOK_URL}"
  cooldown_seconds: 300

logging:
  level: INFO
"""
        # Set environment variable
        os.environ['TEST_WEBHOOK_URL'] = "https://test.webhook.url"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            config = Config(temp_path)
            assert config.lark_webhook == "https://test.webhook.url"
        finally:
            os.unlink(temp_path)
            del os.environ['TEST_WEBHOOK_URL']

    def test_environment_variable_missing(self):
        """Test error when environment variable is missing."""
        config_content = """
exchanges:
  - name: binance
    markets:
      - BTC/USDT

indicators:
  ma_period: 30
  volume_threshold: 3.0
  lookback_bars: 4

alerts:
  lark_webhook: "${MISSING_WEBHOOK_VAR}"
  cooldown_seconds: 300

logging:
  level: INFO
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                Config(temp_path)

            assert "MISSING_WEBHOOK_VAR" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_disabled_exchange(self):
        """Test disabled exchange filtering (TC-F05-04)."""
        config_content = """
exchanges:
  - name: binance
    markets:
      - BTC/USDT
    enabled: true
  - name: okx
    markets:
      - BTC/USDT
    enabled: false

indicators:
  ma_period: 30
  volume_threshold: 3.0
  lookback_bars: 4

alerts:
  lark_webhook: "https://example.com/webhook"

logging:
  level: INFO
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            config = Config(temp_path)
            # Should only return enabled exchanges
            assert len(config.exchanges) == 1
            assert config.exchanges[0]['name'] == 'binance'
        finally:
            os.unlink(temp_path)

    def test_missing_exchanges_section(self):
        """Test error when exchanges section is missing."""
        config_content = """
indicators:
  ma_period: 30

alerts:
  lark_webhook: "https://example.com/webhook"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                Config(temp_path)

            assert "exchanges" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_missing_exchange_name(self):
        """Test error when exchange missing name field."""
        config_content = """
exchanges:
  - markets:
      - BTC/USDT

indicators:
  ma_period: 30
  volume_threshold: 3.0
  lookback_bars: 4

alerts:
  lark_webhook: "https://example.com/webhook"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                Config(temp_path)

            assert "name" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_missing_indicators_section(self):
        """Test error when indicators section is missing."""
        config_content = """
exchanges:
  - name: binance
    markets:
      - BTC/USDT

alerts:
  lark_webhook: "https://example.com/webhook"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                Config(temp_path)

            assert "indicators" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_missing_alerts_section(self):
        """Test error when alerts section is missing."""
        config_content = """
exchanges:
  - name: binance
    markets:
      - BTC/USDT

indicators:
  ma_period: 30
  volume_threshold: 3.0
  lookback_bars: 4
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                Config(temp_path)

            assert "alerts" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_default_logging_config(self):
        """Test default logging configuration."""
        config_content = """
exchanges:
  - name: binance
    markets:
      - BTC/USDT

indicators:
  ma_period: 30
  volume_threshold: 3.0
  lookback_bars: 4

alerts:
  lark_webhook: "https://example.com/webhook"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            config = Config(temp_path)
            # Should have default logging config
            assert config.log_level == 'INFO'
            assert config.log_file == 'logs/signal.log'
        finally:
            os.unlink(temp_path)

    def test_config_properties(self):
        """Test all config property accessors."""
        config_content = """
exchanges:
  - name: binance
    markets:
      - BTC/USDT

indicators:
  ma_period: 25
  ma_type: EMA
  volume_threshold: 2.5
  lookback_bars: 3

alerts:
  lark_webhook: "https://example.com/webhook"
  cooldown_seconds: 600
  rate_limit: 5

logging:
  level: DEBUG
  file: custom.log
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            config = Config(temp_path)
            assert config.ma_period == 25
            assert config.ma_type == "EMA"
            assert config.volume_threshold == 2.5
            assert config.lookback_bars == 3
            assert config.lark_webhook == "https://example.com/webhook"
            assert config.cooldown_seconds == 600
            assert config.rate_limit == 5
            assert config.log_level == "DEBUG"
            assert config.log_file == "custom.log"
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
