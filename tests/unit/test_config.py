"""Unit tests for simulation configuration."""
import os
import pytest
from unittest.mock import patch

from genworlds.simulation.config import (
    SimulationConfig,
    ConfigurationError,
    get_config,
    reload_config,
)


class TestSimulationConfig:
    def test_defaults_are_valid(self):
        config = SimulationConfig()
        assert config.websocket_host == "127.0.0.1"
        assert config.websocket_port == 7456
        assert config.enable_metrics is True

    def test_validation_rejects_invalid_port(self):
        with pytest.raises(ConfigurationError) as exc_info:
            SimulationConfig(websocket_port=70000)
        assert "websocket_port" in str(exc_info.value)

    def test_validation_rejects_negative_reconnect(self):
        with pytest.raises(ConfigurationError) as exc_info:
            SimulationConfig(max_reconnect_attempts=-5)
        assert "max_reconnect_attempts" in str(exc_info.value)

    def test_validation_rejects_invalid_log_level(self):
        with pytest.raises(ConfigurationError) as exc_info:
            SimulationConfig(log_level="NOTREAL")
        assert "log_level" in str(exc_info.value)

    def test_validation_rejects_empty_host(self):
        with pytest.raises(ConfigurationError) as exc_info:
            SimulationConfig(websocket_host="")
        assert "websocket_host" in str(exc_info.value)

    def test_get_websocket_url(self):
        config = SimulationConfig(websocket_host="example.com", websocket_port=9000)
        assert config.get_websocket_url() == "ws://example.com:9000/ws"

    def test_from_env_with_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            config = SimulationConfig.from_env()
            assert config.websocket_host == "127.0.0.1"
            assert config.websocket_port == 7456

    def test_from_env_with_custom_values(self):
        env = {
            "GENWORLDS_HOST": "custom.host",
            "GENWORLDS_PORT": "9999",
            "GENWORLDS_LOG_LEVEL": "DEBUG",
            "GENWORLDS_ENABLE_METRICS": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            config = SimulationConfig.from_env()
            assert config.websocket_host == "custom.host"
            assert config.websocket_port == 9999
            assert config.log_level == "DEBUG"
            assert config.enable_metrics is False

    def test_singleton_returns_same_instance(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_reload_creates_new_instance(self):
        c1 = get_config()
        c2 = reload_config()
        assert c1 is not c2

    def test_valid_port_range(self):
        SimulationConfig(websocket_port=1)
        SimulationConfig(websocket_port=65535)
