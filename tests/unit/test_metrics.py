"""Unit tests for the simulation metrics system."""
import pytest
import time
from genworlds.simulation.metrics import SimulationMetrics, get_metrics


class TestSimulationMetrics:
    def setup_method(self):
        self.metrics = SimulationMetrics()

    def test_record_event_received(self):
        self.metrics.record_event_received("test_event", "agent-1", "target-1")
        summary = self.metrics.get_summary()
        assert summary["events"]["total"] == 1
        assert "test_event" in summary["events"]["by_type"]
        assert summary["events"]["by_type"]["test_event"]["count"] == 1
        assert summary["events"]["by_sender"]["agent-1"] == 1
        assert summary["events"]["by_target"]["target-1"] == 1

    def test_record_event_without_target(self):
        self.metrics.record_event_received("broadcast_event", "agent-2")
        summary = self.metrics.get_summary()
        assert summary["events"]["total"] == 1
        assert "broadcast_event" in summary["events"]["by_type"]
        assert summary["events"]["by_sender"]["agent-2"] == 1
        assert len(summary["events"]["by_target"]) == 0

    def test_record_event_processed_with_latency(self):
        self.metrics.record_event_received("action", "agent-1")
        self.metrics.record_event_processed("action", latency_ms=10.5)
        summary = self.metrics.get_summary()
        assert summary["events"]["by_type"]["action"]["count"] == 1
        assert summary["performance"]["avg_latency_ms"] == 10.5

    def test_record_event_error(self):
        self.metrics.record_event_received("error_event", "agent-1")
        self.metrics.record_event_error("error_event")
        summary = self.metrics.get_summary()
        assert summary["events"]["by_type"]["error_event"]["errors"] == 1
        assert summary["performance"]["error_rate"] == 1.0

    def test_connection_metrics(self):
        self.metrics.record_connection_opened()
        self.metrics.record_connection_opened()
        summary = self.metrics.get_summary()
        assert summary["connections"]["total"] == 2
        assert summary["connections"]["active"] == 2

        self.metrics.record_connection_closed()
        summary = self.metrics.get_summary()
        assert summary["connections"]["active"] == 1
        assert summary["connections"]["disconnections"] == 1

    def test_connection_error_tracking(self):
        self.metrics.record_connection_error()
        self.metrics.record_connection_error()
        summary = self.metrics.get_summary()
        assert summary["connections"]["errors"] == 2

    def test_latency_percentiles(self):
        for latency in [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]:
            self.metrics.record_event_received("action", "agent")
            self.metrics.record_event_processed("action", latency_ms=latency)

        summary = self.metrics.get_summary()
        assert summary["performance"]["p50_latency_ms"] == 25.0
        assert summary["performance"]["p99_latency_ms"] == 50.0

    def test_events_by_type_aggregation(self):
        self.metrics.record_event_received("move", "agent-1")
        self.metrics.record_event_received("move", "agent-2")
        self.metrics.record_event_received("speak", "agent-1")
        self.metrics.record_event_received("interact", "agent-3")

        summary = self.metrics.get_summary()
        assert summary["events"]["total"] == 4
        assert summary["events"]["by_type"]["move"]["count"] == 2
        assert summary["events"]["by_type"]["speak"]["count"] == 1
        assert summary["events"]["by_type"]["interact"]["count"] == 1

    def test_thread_safety(self):
        import threading

        def record_events():
            for i in range(100):
                self.metrics.record_event_received("test_event", f"agent-{i % 5}")
                self.metrics.record_event_processed("test_event", latency_ms=1.0)

        threads = [threading.Thread(target=record_events) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        summary = self.metrics.get_summary()
        assert summary["events"]["total"] == 500
        assert summary["events"]["by_type"]["test_event"]["count"] == 500

    def test_reset_clears_all_metrics(self):
        self.metrics.record_event_received("event1", "agent-1")
        self.metrics.record_connection_opened()
        self.metrics.reset()

        summary = self.metrics.get_summary()
        assert summary["events"]["total"] == 0
        assert summary["connections"]["total"] == 0
        assert summary["connections"]["active"] == 0

    def test_last_occurrence_timestamp(self):
        before = time.time()
        self.metrics.record_event_received("timed_event", "agent-1")
        after = time.time()

        summary = self.metrics.get_summary()
        last_occurrence_str = summary["events"]["by_type"]["timed_event"]["last_occurrence"]
        assert last_occurrence_str is not None

    def test_get_metrics_singleton(self):
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_zero_division_protection(self):
        summary = self.metrics.get_summary()
        assert summary["performance"]["error_rate"] == 0.0
        assert summary["performance"]["events_per_second"] == 0.0
