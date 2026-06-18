"""Unit tests for the WebSocket server."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from genworlds.simulation.sockets.server import WebSocketManager


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
