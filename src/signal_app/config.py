"""Configuration management module."""

import os
from pathlib import Path
from typing import Any, Dict, List
import yaml


class Config:
    """Configuration loader and validator."""

    def __init__(self, config_path: str | None = None):
        """Initialize configuration.

        Args:
            config_path: Path to configuration file. Defaults to config.yaml
                        or env var SIGNAL_CONFIG.
        """
        if config_path is None:
            config_path = os.getenv("SIGNAL_CONFIG", "config.yaml")

        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load and validate configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}\n"
                f"Please create config.yaml or set SIGNAL_CONFIG environment variable."
            )

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Replace environment variables
                content = self._replace_env_vars(content)
                self._config = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")

        self._validate_config()

    def _replace_env_vars(self, content: str) -> str:
        """Replace ${VAR_NAME} with environment variable values."""
        import re
        pattern = r'\$\{([^}]+)\}'

        def replacer(match):
            var_name = match.group(1)
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(
                    f"Environment variable {var_name} not found. "
                    f"Please set it or update config file."
                )
            return value

        return re.sub(pattern, replacer, content)

    def _validate_config(self) -> None:
        """Validate configuration structure."""
        # Validate exchanges
        if 'exchanges' not in self._config:
            raise ValueError("Config must contain 'exchanges' section")

        if not isinstance(self._config['exchanges'], list):
            raise ValueError("'exchanges' must be a list")

        for exchange in self._config['exchanges']:
            if 'name' not in exchange:
                raise ValueError("Each exchange must have 'name' field")
            if 'markets' not in exchange:
                raise ValueError(f"Exchange {exchange['name']} must have 'markets' field")
            if not isinstance(exchange['markets'], list):
                raise ValueError(f"Exchange {exchange['name']} markets must be a list")

        # Validate indicators
        if 'indicators' not in self._config:
            raise ValueError("Config must contain 'indicators' section")

        indicators = self._config['indicators']
        required_indicator_fields = ['ma_period', 'volume_threshold', 'lookback_bars']
        for field in required_indicator_fields:
            if field not in indicators:
                raise ValueError(f"Indicators section must contain '{field}'")

        # Validate alerts
        if 'alerts' not in self._config:
            raise ValueError("Config must contain 'alerts' section")

        alerts = self._config['alerts']
        if 'lark_webhook' not in alerts:
            raise ValueError("Alerts section must contain 'lark_webhook'")

        # Validate logging (optional)
        if 'logging' not in self._config:
            self._config['logging'] = {
                'level': 'INFO',
                'file': 'logs/signal.log'
            }

    @property
    def exchanges(self) -> List[Dict[str, Any]]:
        """Get enabled exchanges configuration."""
        return [
            ex for ex in self._config['exchanges']
            if ex.get('enabled', True)
        ]

    @property
    def ma_period(self) -> int:
        """Get MA period."""
        return int(self._config['indicators']['ma_period'])

    @property
    def ma_type(self) -> str:
        """Get MA type (SMA or EMA)."""
        return self._config['indicators'].get('ma_type', 'SMA')

    @property
    def volume_threshold(self) -> float:
        """Get volume threshold multiplier."""
        return float(self._config['indicators']['volume_threshold'])

    @property
    def lookback_bars(self) -> int:
        """Get lookback bars for high/low detection."""
        return int(self._config['indicators']['lookback_bars'])

    @property
    def breakout_threshold_pct(self) -> float:
        """获取突破幅度阈值百分比。

        Returns:
            突破幅度阈值，默认 0.5%
        """
        return float(self._config['indicators'].get('breakout_threshold_pct', 0.5))

    @property
    def historical_bars(self) -> int:
        """获取启动时加载的历史K线数量。

        Returns:
            历史K线数量，默认 100
        """
        return int(self._config['indicators'].get('historical_bars', 100))

    @property
    def lark_webhook(self) -> str:
        """Get Lark webhook URL."""
        return self._config['alerts']['lark_webhook']

    @property
    def cooldown_seconds(self) -> int:
        """Get alert cooldown period in seconds."""
        return int(self._config['alerts'].get('cooldown_seconds', 300))

    @property
    def rate_limit(self) -> int:
        """Get rate limit (messages per minute)."""
        return int(self._config['alerts'].get('rate_limit', 10))

    @property
    def mention_user_id(self) -> str | None:
        """Get Lark user ID to mention in alerts (optional).

        Returns:
            User open_id or None if not configured
        """
        return self._config['alerts'].get('mention_user_id')

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config['logging']['level']

    @property
    def log_file(self) -> str:
        """Get log file path."""
        return self._config['logging']['file']
