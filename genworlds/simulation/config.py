"""Configuration management for GenWorlds simulations.

Provides centralized configuration with validation, environment variable support,
and sensible defaults for production deployments.

Example:
    >>> from genworlds.simulation.config import get_config
    >>> config = get_config()
    >>> print(config.websocket_host)
    127.0.0.1
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, List


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


@dataclass
class SimulationConfig:
    """Configuration for a GenWorlds simulation.

    All values can be overridden via environment variables with the GENWORLDS_ prefix.

    Attributes:
        websocket_host: Host address for WebSocket server
        websocket_port: Port for WebSocket server
        websocket_ping_interval: Ping interval in seconds for keepalive
        websocket_ping_timeout: Ping timeout in seconds
        reconnect_interval: Interval between reconnection attempts
        max_reconnect_attempts: Maximum reconnection attempts before giving up
        max_latency_samples: Maximum latency samples to retain for metrics
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_metrics: Whether to enable metrics collection
    """

    websocket_host: str = "127.0.0.1"
    websocket_port: int = 7456
    websocket_ping_interval: int = 600
    websocket_ping_timeout: int = 600
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    max_latency_samples: int = 1000
    log_level: str = "INFO"
    enable_metrics: bool = True

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate all configuration values.

        Raises:
            ConfigurationError: If any value is invalid
        """
        errors = []

        if not isinstance(self.websocket_host, str) or not self.websocket_host:
            errors.append("websocket_host must be a non-empty string")

        if not (1 <= self.websocket_port <= 65535):
            errors.append(f"websocket_port must be between 1 and 65535, got {self.websocket_port}")

        if self.websocket_ping_interval < 0:
            errors.append("websocket_ping_interval must be non-negative")

        if self.websocket_ping_timeout < 0:
            errors.append("websocket_ping_timeout must be non-negative")

        if self.reconnect_interval < 0:
            errors.append("reconnect_interval must be non-negative")

        if self.max_reconnect_attempts < 0:
            errors.append("max_reconnect_attempts must be non-negative")

        if self.max_latency_samples < 1:
            errors.append("max_latency_samples must be at least 1")

        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            errors.append(f"log_level must be one of {valid_levels}, got {self.log_level}")

        if errors:
            raise ConfigurationError(
                "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

    @classmethod
    def from_env(cls) -> SimulationConfig:
        """Create configuration from environment variables.

        Environment variables:
            GENWORLDS_HOST: WebSocket host
            GENWORLDS_PORT: WebSocket port
            GENWORLDS_PING_INTERVAL: Ping interval
            GENWORLDS_PING_TIMEOUT: Ping timeout
            GENWORLDS_RECONNECT_INTERVAL: Reconnect interval
            GENWORLDS_MAX_RECONNECT: Max reconnect attempts
            GENWORLDS_LOG_LEVEL: Log level
            GENWORLDS_ENABLE_METRICS: Enable metrics (true/false)

        Returns:
            SimulationConfig with values from environment or defaults
        """
        def get_env_int(key: str, default: int) -> int:
            val = os.environ.get(key)
            return int(val) if val else default

        def get_env_bool(key: str, default: bool) -> bool:
            val = os.environ.get(key)
            if val is None:
                return default
            return val.lower() in ("true", "1", "yes", "on")

        return cls(
            websocket_host=os.environ.get("GENWORLDS_HOST", "127.0.0.1"),
            websocket_port=get_env_int("GENWORLDS_PORT", 7456),
            websocket_ping_interval=get_env_int("GENWORLDS_PING_INTERVAL", 600),
            websocket_ping_timeout=get_env_int("GENWORLDS_PING_TIMEOUT", 600),
            reconnect_interval=get_env_int("GENWORLDS_RECONNECT_INTERVAL", 5),
            max_reconnect_attempts=get_env_int("GENWORLDS_MAX_RECONNECT", 10),
            log_level=os.environ.get("GENWORLDS_LOG_LEVEL", "INFO"),
            enable_metrics=get_env_bool("GENWORLDS_ENABLE_METRICS", True),
        )

    def get_websocket_url(self) -> str:
        """Get the full WebSocket URL for this configuration."""
        return f"ws://{self.websocket_host}:{self.websocket_port}/ws"


_config: Optional[SimulationConfig] = None


def get_config() -> SimulationConfig:
    """Get the global configuration singleton.

    Loads from environment on first call.

    Returns:
        The global SimulationConfig instance
    """
    global _config
    if _config is None:
        _config = SimulationConfig.from_env()
    return _config


def reload_config() -> SimulationConfig:
    """Force reload configuration from environment.

    Returns:
        New SimulationConfig instance from environment
    """
    global _config
    _config = SimulationConfig.from_env()
    return _config
