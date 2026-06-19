from __future__ import annotations

import asyncio
import argparse
import json
import logging
import signal
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import List, Dict

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse

from genworlds.simulation.metrics import get_metrics

logger = logging.getLogger(__name__)

_shutdown_event: asyncio.Event | None = None


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._connection_metadata: Dict[str, dict] = {}
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def connect(self, websocket: WebSocket, client_id: str | None = None):
        await websocket.accept()
        async with self._get_lock():
            self.active_connections.append(websocket)
            if client_id:
                self._connection_metadata[client_id] = {
                    "connected_at": time.time(),
                    "websocket": websocket,
                }
        get_metrics().record_connection_opened()

    async def disconnect(self, websocket: WebSocket):
        async with self._get_lock():
            try:
                self.active_connections.remove(websocket)
            except ValueError:
                pass
            stale_ids = [
                cid for cid, meta in self._connection_metadata.items()
                if meta.get("websocket") == websocket
            ]
            for cid in stale_ids:
                del self._connection_metadata[cid]
        get_metrics().record_connection_closed()

    async def send_to_client(self, client_id: str, data: str) -> bool:
        async with self._get_lock():
            meta = self._connection_metadata.get(client_id)
            if meta is None:
                return False
            ws = meta["websocket"]
        try:
            await ws.send_text(data)
            return True
        except Exception as e:
            logger.warning("Failed to send to client %s: %s", client_id, e)
            await self.disconnect(ws)
            return False

    async def broadcast(self, data: str, event_type: str | None = None, exclude: WebSocket | None = None):
        async with self._get_lock():
            connections = [ws for ws in self.active_connections if ws != exclude]

        stale: List[WebSocket] = []
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
                        stale_ids = [
                            cid for cid, meta in self._connection_metadata.items()
                            if meta.get("websocket") == ws
                        ]
                        for cid in stale_ids:
                            del self._connection_metadata[cid]
                    except ValueError:
                        pass

    def get_client_count(self) -> int:
        return len(self.active_connections)

    def get_client_ids(self) -> List[str]:
        return list(self._connection_metadata.keys())

    async def send_update(self, data: str, event_type: str | None = None):
        await self.broadcast(data, event_type)


websocket_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info("Received signal %d, initiating shutdown", signum)
        if _shutdown_event:
            _shutdown_event.set()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    yield

    logger.info("Simulation socket server shutting down.")
    get_metrics().reset()


app = FastAPI(lifespan=lifespan)


@app.get("/metrics")
async def get_metrics_endpoint():
    """Return simulation metrics as JSON."""
    return JSONResponse(content=get_metrics().get_summary())


@app.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Return metrics in Prometheus text format for monitoring integration."""
    metrics = get_metrics()
    summary = metrics.get_summary()

    lines = []
    lines.append("# HELP genworlds_uptime_seconds Time since server start")
    lines.append("# TYPE genworlds_uptime_seconds gauge")
    lines.append(f"genworlds_uptime_seconds {summary['uptime_seconds']}")

    lines.append("# HELP genworlds_events_total Total events processed")
    lines.append("# TYPE genworlds_events_total counter")
    lines.append(f"genworlds_events_total {summary['events']['total']}")

    lines.append("# HELP genworlds_connections_active Active WebSocket connections")
    lines.append("# TYPE genworlds_connections_active gauge")
    lines.append(f"genworlds_connections_active {summary['connections']['active']}")

    lines.append("# HELP genworlds_connections_total Total connections opened")
    lines.append("# TYPE genworlds_connections_total counter")
    lines.append(f"genworlds_connections_total {summary['connections']['total']}")

    lines.append("# HELP genworlds_errors_total Total processing errors")
    lines.append("# TYPE genworlds_errors_total counter")
    total_errors = sum(m['errors'] for m in summary['events']['by_type'].values())
    lines.append(f"genworlds_errors_total {total_errors}")

    lines.append("# HELP genworlds_latency_avg_ms Average event processing latency")
    lines.append("# TYPE genworlds_latency_avg_ms gauge")
    lines.append(f"genworlds_latency_avg_ms {summary['performance']['avg_latency_ms']}")

    lines.append("# HELP genworlds_latency_p50_ms P50 event processing latency")
    lines.append("# TYPE genworlds_latency_p50_ms gauge")
    lines.append(f"genworlds_latency_p50_ms {summary['performance']['p50_latency_ms']}")

    lines.append("# HELP genworlds_latency_p99_ms P99 event processing latency")
    lines.append("# TYPE genworlds_latency_p99_ms gauge")
    lines.append(f"genworlds_latency_p99_ms {summary['performance']['p99_latency_ms']}")

    lines.append("# HELP genworlds_events_per_second Event throughput")
    lines.append("# TYPE genworlds_events_per_second gauge")
    lines.append(f"genworlds_events_per_second {summary['performance']['events_per_second']}")

    return PlainTextResponse("\n".join(lines) + "\n")


@app.get("/metrics/reset")
async def reset_metrics():
    """Reset all collected metrics."""
    get_metrics().reset()
    return {"status": "reset"}


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}


@app.get("/connections")
async def get_connections():
    """Return information about active connections."""
    return JSONResponse({
        "active_count": websocket_manager.get_client_count(),
        "client_ids": websocket_manager.get_client_ids(),
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = None
    try:
        await websocket_manager.connect(websocket)
        while True:
            if _shutdown_event and _shutdown_event.is_set():
                logger.info("Server shutting down, closing connection")
                break
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                continue
            logger.debug("Received: %s", data)
            metrics = get_metrics()
            try:
                event = json.loads(data)
                event_type = event.get("event_type", "unknown")
                sender_id = event.get("sender_id", "unknown")
                target_id = event.get("target_id")
                if client_id is None:
                    client_id = sender_id
                metrics.record_event_received(event_type, sender_id, target_id)
                send_start = time.perf_counter()
                await websocket_manager.broadcast(data, event_type, exclude=websocket)
                latency_ms = (time.perf_counter() - send_start) * 1000
                metrics.record_event_processed(event_type, latency_ms)
            except json.JSONDecodeError:
                metrics.record_event_received("invalid_json", "unknown")
                get_metrics().record_event_error("invalid_json")
                await websocket_manager.broadcast(data)
    except WebSocketDisconnect as e:
        logger.info("Client %s disconnected (code=%s)", client_id or "unknown", e.code)
    except Exception as e:
        logger.error("WebSocket handler error for %s: %s", client_id or "unknown", e, exc_info=True)
        get_metrics().record_event_error("handler_exception")
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
