"""Event metrics and monitoring for GenWorlds simulations.

This module provides thread-safe metrics collection for production observability
of multi-agent simulations. It tracks event throughput, latency, errors, and
connection health.

Example usage:
    >>> from genworlds.simulation.metrics import get_metrics
    >>> metrics = get_metrics()
    >>> metrics.record_event_received("agent_action", "agent-1")
    >>> metrics.record_event_processed("agent_action", latency_ms=10.5)
    >>> summary = metrics.get_summary()
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class EventMetric:
    """Tracks aggregated metrics for a specific event type.

    Attributes:
        count: Total number of events of this type received
        errors: Number of processing errors for this event type
        total_latency_ms: Cumulative processing latency in milliseconds
        last_occurrence: Timestamp of the most recent event
    """
    count: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    last_occurrence: Optional[datetime] = None


@dataclass
class ConnectionMetric:
    """Tracks WebSocket connection lifecycle metrics.

    Attributes:
        total_connections: Cumulative count of connections since startup
        active_connections: Current number of open connections
        total_disconnections: Cumulative count of disconnections
        total_errors: Cumulative count of connection errors
    """
    total_connections: int = 0
    active_connections: int = 0
    total_disconnections: int = 0
    total_errors: int = 0


class SimulationMetrics:
    """Thread-safe metrics collection for GenWorlds simulations.

    This class provides comprehensive observability for production deployments,
    including event throughput tracking, latency percentiles, error rates,
    and connection health monitoring.

    Thread Safety:
        All public methods are thread-safe and can be called concurrently.

    Example:
        >>> metrics = SimulationMetrics()
        >>> metrics.record_event_received("agent_action", "agent-1")
        >>> metrics.record_event_processed("agent_action", latency_ms=12.5)
        >>> summary = metrics.get_summary()
        >>> print(summary["events"]["total"])
        1

    Attributes:
        _max_latency_samples: Maximum number of latency samples to retain for percentile calculation
    """

    def __init__(self, max_latency_samples: int = 1000):
        self._lock = threading.RLock()
        self._event_metrics: Dict[str, EventMetric] = defaultdict(EventMetric)
        self._sender_counts: Dict[str, int] = defaultdict(int)
        self._target_counts: Dict[str, int] = defaultdict(int)
        self._connection = ConnectionMetric()
        self._start_time = datetime.now()
        self._latency_samples: List[float] = []
        self._max_latency_samples = max_latency_samples

    def record_event_received(self, event_type: str, sender_id: str, target_id: Optional[str] = None) -> None:
        """Record that an event was received for processing.

        Args:
            event_type: The type identifier of the event (e.g., "agent_action")
            sender_id: ID of the entity that sent the event
            target_id: Optional ID of the target entity. If None, event is a broadcast.
        """
        with self._lock:
            self._event_metrics[event_type].count += 1
            self._event_metrics[event_type].last_occurrence = datetime.now()
            self._sender_counts[sender_id] += 1
            if target_id:
                self._target_counts[target_id] += 1

    def record_event_processed(self, event_type: str, latency_ms: Optional[float] = None) -> None:
        """Record successful event processing with optional latency measurement.

        Args:
            event_type: The type identifier of the processed event
            latency_ms: Optional processing latency in milliseconds. If provided,
                this is added to the rolling latency sample buffer for percentile calculation.
        """
        with self._lock:
            if latency_ms is not None:
                self._event_metrics[event_type].total_latency_ms += latency_ms
                self._latency_samples.append(latency_ms)
                if len(self._latency_samples) > self._max_latency_samples:
                    self._latency_samples = self._latency_samples[-self._max_latency_samples:]

    def record_event_error(self, event_type: str) -> None:
        """Record an event processing error.

        Args:
            event_type: The type identifier of the event that failed to process
        """
        with self._lock:
            self._event_metrics[event_type].errors += 1

    def record_connection_opened(self) -> None:
        """Record a new WebSocket connection being established."""
        with self._lock:
            self._connection.total_connections += 1
            self._connection.active_connections += 1

    def record_connection_closed(self) -> None:
        """Record a WebSocket connection being closed."""
        with self._lock:
            self._connection.active_connections = max(0, self._connection.active_connections - 1)
            self._connection.total_disconnections += 1

    def record_connection_error(self) -> None:
        """Record a connection error (e.g., send failure, unexpected disconnect)."""
        with self._lock:
            self._connection.total_errors += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of all collected metrics.

        Returns a nested dictionary containing:
        - uptime_seconds: Time since metrics collection started
        - events: Event counts by type, sender, and target
        - connections: Connection lifecycle statistics
        - performance: Aggregate metrics including throughput, error rate, latency percentiles

        Returns:
            Dict containing complete metrics snapshot suitable for JSON serialization
        """
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

    def reset(self) -> None:
        """Reset all metrics to initial state.

        Clears all counters, latency samples, and resets the start time.
        Thread-safe and can be called at runtime.
        """
        with self._lock:
            self._event_metrics.clear()
            self._sender_counts.clear()
            self._target_counts.clear()
            self._connection = ConnectionMetric()
            self._start_time = datetime.now()
            self._latency_samples.clear()


_metrics: Optional[SimulationMetrics] = None
_metrics_lock = threading.Lock()


def get_metrics() -> SimulationMetrics:
    """Get the global metrics singleton instance.

    Returns the same SimulationMetrics instance across all calls, creating it
    on first invocation. Thread-safe.

    Returns:
        SimulationMetrics: The global metrics collection instance
    """
    global _metrics
    if _metrics is None:
        with _metrics_lock:
            if _metrics is None:
                _metrics = SimulationMetrics()
    return _metrics
