"""Event metrics and monitoring for GenWorlds simulations."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class EventMetric:
    """Tracks metrics for a specific event type."""
    count: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    last_occurrence: datetime | None = None


@dataclass
class ConnectionMetric:
    """Tracks connection lifecycle metrics."""
    total_connections: int = 0
    active_connections: int = 0
    total_disconnections: int = 0
    total_errors: int = 0


class SimulationMetrics:
    """
    Thread-safe metrics collection for GenWorlds simulations.

    Tracks:
    - Event counts by type, sender, target
    - Event processing latency
    - Connection statistics
    - Error rates

    Example:
        metrics = SimulationMetrics()
        metrics.record_event_received("agent_action", "agent-1")
        metrics.record_event_processed("agent_action", latency_ms=12.5)
        metrics.get_summary()  # Returns dict of all metrics
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._event_metrics: Dict[str, EventMetric] = defaultdict(EventMetric)
        self._sender_counts: Dict[str, int] = defaultdict(int)
        self._target_counts: Dict[str, int] = defaultdict(int)
        self._connection = ConnectionMetric()
        self._start_time = datetime.now()
        self._latency_samples: List[float] = []
        self._max_latency_samples = 1000

    def record_event_received(self, event_type: str, sender_id: str, target_id: str | None = None):
        """Record that an event was received for processing."""
        with self._lock:
            self._event_metrics[event_type].count += 1
            self._event_metrics[event_type].last_occurrence = datetime.now()
            self._sender_counts[sender_id] += 1
            if target_id:
                self._target_counts[target_id] += 1

    def record_event_processed(self, event_type: str, latency_ms: float | None = None):
        """Record successful event processing with optional latency."""
        with self._lock:
            if latency_ms is not None:
                self._event_metrics[event_type].total_latency_ms += latency_ms
                self._latency_samples.append(latency_ms)
                if len(self._latency_samples) > self._max_latency_samples:
                    self._latency_samples = self._latency_samples[-self._max_latency_samples:]

    def record_event_error(self, event_type: str):
        """Record an event processing error."""
        with self._lock:
            self._event_metrics[event_type].errors += 1

    def record_connection_opened(self):
        """Record a new WebSocket connection."""
        with self._lock:
            self._connection.total_connections += 1
            self._connection.active_connections += 1

    def record_connection_closed(self):
        """Record a WebSocket disconnection."""
        with self._lock:
            self._connection.active_connections = max(0, self._connection.active_connections - 1)
            self._connection.total_disconnections += 1

    def record_connection_error(self):
        """Record a connection error."""
        with self._lock:
            self._connection.total_errors += 1

    def get_summary(self) -> dict:
        """Get a comprehensive summary of all metrics."""
        with self._lock:
            uptime_seconds = (datetime.now() - self._start_time).total_seconds()
            total_events = sum(m.count for m in self._event_metrics.values())
            total_errors = sum(m.errors for m in self._event_metrics.values())

            avg_latency = 0.0
            p50_latency = 0.0
            p99_latency = 0.0
            if self._latency_samples:
                avg_latency = sum(self._latency_samples) / len(self._latency_samples)
                sorted_latencies = sorted(self._latency_samples)
                p50_idx = int(len(sorted_latencies) * 0.5)
                p99_idx = int(len(sorted_latencies) * 0.99)
                p50_latency = sorted_latencies[p50_idx]
                p99_latency = sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)]

            events_per_second = total_events / uptime_seconds if uptime_seconds > 0 else 0.0

            return {
                "uptime_seconds": uptime_seconds,
                "events": {
                    "total": total_events,
                    "by_type": {
                        event_type: {
                            "count": m.count,
                            "errors": m.errors,
                            "avg_latency_ms": m.total_latency_ms / m.count if m.count > 0 else 0.0,
                            "last_occurrence": m.last_occurrence.isoformat() if m.last_occurrence else None,
                        }
                        for event_type, m in self._event_metrics.items()
                    },
                    "by_sender": dict(self._sender_counts),
                    "by_target": dict(self._target_counts),
                },
                "connections": {
                    "total": self._connection.total_connections,
                    "active": self._connection.active_connections,
                    "disconnections": self._connection.total_disconnections,
                    "errors": self._connection.total_errors,
                },
                "performance": {
                    "events_per_second": events_per_second,
                    "error_rate": total_errors / total_events if total_events > 0 else 0.0,
                    "avg_latency_ms": avg_latency,
                    "p50_latency_ms": p50_latency,
                    "p99_latency_ms": p99_latency,
                },
            }

    def reset(self):
        """Reset all metrics to initial state."""
        with self._lock:
            self._event_metrics.clear()
            self._sender_counts.clear()
            self._target_counts.clear()
            self._connection = ConnectionMetric()
            self._start_time = datetime.now()
            self._latency_samples.clear()


# Global metrics instance
_metrics: SimulationMetrics | None = None
_metrics_lock = threading.Lock()


def get_metrics() -> SimulationMetrics:
    """Get the global metrics instance (singleton)."""
    global _metrics
    if _metrics is None:
        with _metrics_lock:
            if _metrics is None:
                _metrics = SimulationMetrics()
    return _metrics
