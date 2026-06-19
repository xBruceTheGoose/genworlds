# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-06-19

### Added

#### Real-time Metrics and Monitoring System
- New `genworlds.simulation.metrics` module for production observability
- Thread-safe event counting by type, sender, and target
- Latency tracking with p50/p99 percentile calculations
- Connection lifecycle monitoring (opens, closes, errors)
- WebSocket server integration with automatic metric collection
- REST endpoints:
  - `GET /metrics` - JSON metrics snapshot
  - `GET /metrics/prometheus` - Prometheus-compatible text format
  - `GET /metrics/reset` - Reset all metrics counters
  - `GET /connections` - Active connection details
  - `GET /health` - Health check for load balancers

#### Configuration Management
- New `genworlds.simulation.config` module with validation
- Environment variable support (`GENWORLDS_*` prefix)
- Configurable ping intervals, reconnection settings, log levels
- `ConfigurationError` exception for invalid configs
- Singleton pattern with `get_config()` and `reload_config()`

#### Enhanced WebSocket Server
- Graceful shutdown handling via signal handlers (SIGTERM, SIGINT)
- Client connection metadata tracking
- Targeted message sending to specific clients
- Broadcast with exclusion support
- Connection timeout handling

#### Improved WebSocket Client
- Maximum reconnection attempts with backoff
- Connection state tracking (`is_connected()`, `wait_for_connection()`)
- Explicit `close()` method for graceful disconnection
- `ConnectionException` for connection failures
- Protected callback execution in error handlers

#### Enhanced Agent System
- `AgentException` for unrecoverable agent errors
- Consecutive error counting with automatic shutdown threshold
- Graceful shutdown support via `shutdown()` method
- Connection timeout during startup (30s)
- Improved logging throughout cognitive loop

### Fixed
- `TestClient` class in `genworlds.simulation.sockets.test_client` referenced
  undefined `self.uri` attribute instead of `self.url`

### Improved
- Comprehensive type hints across all core modules
- Detailed docstrings for public APIs
- Enhanced logging coverage with contextual information
- Thread safety guarantees documented

### Testing
- Added `tests/integration/` directory structure
- Integration tests for metrics system (`test_websocket_integration.py`)
- Unit tests for configuration (`test_config.py`)
- Extended server tests for new endpoints
- Prometheus endpoint format validation

## [0.1.0] - Initial Release

- Event-based multi-agent simulation framework
- WebSocket communication bus
- Abstract agent, object, and world classes
- Langchain and OpenAI integration
- Memory management with Qdrant
- Docusaurus documentation site
