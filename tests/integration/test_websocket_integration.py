"""Integration tests for WebSocket server with metrics."""
import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from genworlds.simulation.metrics import SimulationMetrics, get_metrics


class TestMetricsIntegration:
    def setup_method(self):
        self.metrics = SimulationMetrics()

    @pytest.mark.asyncio
    async def test_full_event_lifecycle_with_metrics(self):
        event = {
            "event_type": "agent_action",
            "sender_id": "agent-1",
            "target_id": "object-1",
            "description": "Test action",
        }
        self.metrics.record_event_received(
            event["event_type"], event["sender_id"], event["target_id"]
        )
        self.metrics.record_event_processed(event["event_type"], latency_ms=15.0)

        summary = self.metrics.get_summary()
        assert summary["events"]["total"] == 1
        assert summary["events"]["by_type"]["agent_action"]["count"] == 1
        assert summary["events"]["by_type"]["agent_action"]["avg_latency_ms"] == 15.0
        assert summary["events"]["by_sender"]["agent-1"] == 1
        assert summary["events"]["by_target"]["object-1"] == 1

    @pytest.mark.asyncio
    async def test_connection_open_close_cycle(self):
        self.metrics.record_connection_opened()
        assert self.metrics.get_summary()["connections"]["active"] == 1

        self.metrics.record_connection_opened()
        assert self.metrics.get_summary()["connections"]["active"] == 2

        self.metrics.record_connection_closed()
        summary = self.metrics.get_summary()
        assert summary["connections"]["active"] == 1
        assert summary["connections"]["total"] == 2
        assert summary["connections"]["disconnections"] == 1

    @pytest.mark.asyncio
    async def test_high_throughput_metrics(self):
        for i in range(100):
            self.metrics.record_event_received(
                f"event_type_{i % 5}", f"agent-{i % 10}", f"target-{i % 3}"
            )
            self.metrics.record_event_processed(f"event_type_{i % 5}", latency_ms=5.0 + i)

        summary = self.metrics.get_summary()
        assert summary["events"]["total"] == 100
        assert len(summary["events"]["by_type"]) == 5
        assert len(summary["events"]["by_sender"]) == 10
        assert len(summary["events"]["by_target"]) == 3
        assert summary["performance"]["avg_latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_error_tracking(self):
        for _ in range(10):
            self.metrics.record_event_received("critical_event", "agent-1")
        for _ in range(3):
            self.metrics.record_event_error("critical_event")

        summary = self.metrics.get_summary()
        assert summary["events"]["by_type"]["critical_event"]["count"] == 10
        assert summary["events"]["by_type"]["critical_event"]["errors"] == 3
        assert summary["performance"]["error_rate"] == 0.3

    @pytest.mark.asyncio
    async def test_percentile_calculation(self):
        latencies = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0] * 10
        for lat in latencies:
            self.metrics.record_event_received("action", "agent")
            self.metrics.record_event_processed("action", latency_ms=lat)

        summary = self.metrics.get_summary()
        assert summary["performance"]["p50_latency_ms"] >= 25.0
        assert summary["performance"]["p99_latency_ms"] >= 49.0


class TestMetricsSingleton:
    def test_singleton_returns_same_instance(self):
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_singleton_persists_across_calls(self):
        metrics = get_metrics()
        metrics.record_event_received("test", "sender")
        assert get_metrics().get_summary()["events"]["total"] >= 1
