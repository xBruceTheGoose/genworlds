import json
import logging
import threading
import time
from typing import Callable, Optional

import websocket

logger = logging.getLogger(__name__)


class ConnectionException(Exception):
    """Raised when WebSocket connection fails after max attempts."""
    pass


class SimulationSocketClient:
    def __init__(
        self,
        process_event: Callable[[dict], None],
        url: str = "ws://127.0.0.1:7456/ws",
        send_initial_event: Optional[Callable[[], None]] = None,
        on_open_callback: Optional[Callable[[], None]] = None,
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = 10,
    ) -> None:
        self.url = url
        self.process_event = process_event
        self.send_initial_event = send_initial_event
        self.on_open_callback = on_open_callback
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_count = 0
        self._connected = threading.Event()
        self._shutdown = threading.Event()
        self.websocket = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

    def on_open(self, ws):
        self._connected.set()
        self._reconnect_count = 0
        logger.info("Connected to simulation socket at %s", self.url)
        if self.send_initial_event:
            try:
                self.send_initial_event()
            except Exception:
                logger.exception("Error in send_initial_event callback")
        if self.on_open_callback:
            try:
                self.on_open_callback()
            except Exception:
                logger.exception("Error in on_open_callback")

    def on_error(self, ws, error):
        logger.error("Simulation socket error: %s", error, exc_info=True)

    def on_close(self, ws, close_status_code, close_msg):
        self._connected.clear()
        logger.info(
            "Simulation socket closed (code=%s msg=%s)", close_status_code, close_msg
        )
        if self._shutdown.is_set():
            logger.info("Shutdown requested, not reconnecting")
            return
        if self.reconnect_interval > 0:
            self._reconnect_count += 1
            if self._reconnect_count > self.max_reconnect_attempts:
                logger.error(
                    "Max reconnect attempts (%d) reached, giving up",
                    self.max_reconnect_attempts,
                )
                return
            logger.info(
                "Reconnecting in %s seconds... (attempt %d/%d)",
                self.reconnect_interval,
                self._reconnect_count,
                self.max_reconnect_attempts,
            )
            time.sleep(self.reconnect_interval)
            self.websocket.run_forever()

    def on_message(self, ws, message):
        logger.debug("Received: %s", message)
        try:
            self.process_event(json.loads(message))
        except json.JSONDecodeError:
            logger.warning("Could not parse message as JSON: %s", message[:200])
        except Exception:
            logger.exception("Error processing message")

    def send_message(self, message: str) -> bool:
        try:
            self.websocket.send(message)
            logger.debug("Sent: %s", message)
            return True
        except Exception:
            logger.exception("Error sending message")
            return False

    def is_connected(self) -> bool:
        return self._connected.is_set()

    def wait_for_connection(self, timeout: float | None = None) -> bool:
        return self._connected.wait(timeout=timeout)

    def close(self):
        self._shutdown.set()
        try:
            self.websocket.close()
        except Exception:
            logger.debug("Error closing WebSocket (may already be closed)")
        logger.info("Client shutdown complete")
