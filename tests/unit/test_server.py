"""Unit tests for the WebSocket server."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from genworlds.simulation.sockets.server import WebSocketManager, app
from genworlds.simulation.metrics import SimulationMetrics


class TestWebSocketManager:
    def setup_method(self):
        self.manager = WebSocketManager()

    @pytest.mark.asyncio
    async def test_connect_adds_to_active(self):
        ws = AsyncMock()
        await self.manager.connect(ws)
        assert ws in self.manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_active(self):
        ws = AsyncMock()
        await self.manager.connect(ws)
        await self.manager.disconnect(ws)
        assert ws not in self.manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_tolerates_missing(self):
        ws = AsyncMock()
        # Should not raise even if ws was never connected
        await self.manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_send_update_delivers_to_all(self):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await self.manager.connect(ws1)
        await self.manager.connect(ws2)
        await self.manager.send_update("hello")
        ws1.send_text.assert_awaited_once_with("hello")
        ws2.send_text.assert_awaited_once_with("hello")

    @pytest.mark.asyncio
    async def test_send_update_removes_stale_connections(self):
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_text.side_effect = RuntimeError("websocket.close")
        await self.manager.connect(ws_good)
        await self.manager.connect(ws_bad)
        await self.manager.send_update("data")
        assert ws_bad not in self.manager.active_connections
        assert ws_good in self.manager.active_connections


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_json(self):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "connections" in data
        assert "performance" in data

    @pytest.mark.asyncio
    async def test_prometheus_endpoint_returns_text(self):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/metrics/prometheus")
        assert response.status_code == 200
        text = response.text
        assert "genworlds_uptime_seconds" in text
        assert "genworlds_events_total" in text
        assert "genworlds_connections_active" in text
        assert "# TYPE" in text
        assert "# HELP" in text

    @pytest.mark.asyncio
    async def test_metrics_reset_endpoint(self):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/metrics/reset")
        assert response.status_code == 200
        assert response.json()["status"] == "reset"

    @pytest.mark.asyncio
    async def test_connections_endpoint(self):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/connections")
        assert response.status_code == 200
        data = response.json()
        assert "active_count" in data
        assert "client_ids" in data
