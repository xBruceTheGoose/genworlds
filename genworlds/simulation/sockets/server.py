from __future__ import annotations

import asyncio
import argparse
import json
import logging
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from genworlds.simulation.metrics import get_metrics

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._get_lock():
            self.active_connections.append(websocket)
        get_metrics().record_connection_opened()

    async def disconnect(self, websocket: WebSocket):
        async with self._get_lock():
            try:
                self.active_connections.remove(websocket)
            except ValueError:
                pass
        get_metrics().record_connection_closed()

    async def send_update(self, data: str, event_type: str | None = None):
        async with self._get_lock():
            connections = list(self.active_connections)

        stale: List[WebSocket] = []
        send_start = time.perf_counter()
        for connection in connections:
            try:
                await connection.send_text(data)
            except RuntimeError as e:
                if "websocket.close" in str(e) or "Unexpected ASGI" in str(e):
                    stale.append(connection)
                    get_metrics().record_connection_error()
                else:
                    logger.warning("WebSocket send error: %s", e)
                    get_metrics().record_connection_error()
            except Exception as e:
                logger.warning("WebSocket send error: %s", e)
                stale.append(connection)
                get_metrics().record_connection_error()

        if stale:
            async with self._get_lock():
                for ws in stale:
                    try:
                        self.active_connections.remove(ws)
                    except ValueError:
                        pass


websocket_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    logger.info("Simulation socket server shutting down.")


app = FastAPI(lifespan=lifespan)


@app.get("/metrics")
async def get_metrics_endpoint():
    """Return simulation metrics as JSON."""
    return JSONResponse(content=get_metrics().get_summary())


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Received: %s", data)
            metrics = get_metrics()
            try:
                event = json.loads(data)
                event_type = event.get("event_type", "unknown")
                sender_id = event.get("sender_id", "unknown")
                target_id = event.get("target_id")
                metrics.record_event_received(event_type, sender_id, target_id)
                send_start = time.perf_counter()
                await websocket_manager.send_update(data, event_type)
                latency_ms = (time.perf_counter() - send_start) * 1000
                metrics.record_event_processed(event_type, latency_ms)
            except json.JSONDecodeError:
                metrics.record_event_received("invalid_json", "unknown")
                await websocket_manager.send_update(data)
    except WebSocketDisconnect as e:
        logger.info("Client disconnected (code=%s)", e.code)
    except Exception as e:
        logger.error("WebSocket handler error: %s", e, exc_info=True)
    finally:
        await websocket_manager.disconnect(websocket)


def start(
    host: str = "127.0.0.1",
    port: int = 7456,
    silent: bool = False,
    ws_ping_interval: int = 600,
    ws_ping_timeout: int = 600,
    timeout_keep_alive: int = 60,
):
    log_level = "warning" if silent else "info"
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        ws_ping_interval=ws_ping_interval,
        ws_ping_timeout=ws_ping_timeout,
        timeout_keep_alive=timeout_keep_alive,
    )


def start_thread(host: str = "127.0.0.1", port: int = 7456, silent: bool = False):
    threading.Thread(
        target=start,
        name="WebSocket Server Thread",
        daemon=True,
        kwargs={"host": host, "port": port, "silent": silent},
    ).start()


def parse_args():
    parser = argparse.ArgumentParser(description="Start the world socket server.")
    parser.add_argument("--port", type=int, default=7456, nargs="?")
    parser.add_argument("--host", type=str, default="127.0.0.1", nargs="?")
    return parser.parse_args()


def start_from_command_line():
    args = parse_args()
    try:
        start(host=args.host, port=args.port)
    except BaseException as e:
        logger.error(e)
        sys.exit(0)


if __name__ == "__main__":
    start_from_command_line()
