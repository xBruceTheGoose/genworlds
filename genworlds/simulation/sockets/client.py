import json
import logging
import time
from typing import Callable, Optional

import websocket

logger = logging.getLogger(__name__)


class SimulationSocketClient:
    def __init__(
        self,
        process_event: Callable[[dict], None],
        url: str = "ws://127.0.0.1:7456/ws",
        send_initial_event: Optional[Callable[[], None]] = None,
        on_open_callback: Optional[Callable[[], None]] = None,
        reconnect_interval: int = 5,
    ) -> None:
        self.url = url
        self.process_event = process_event
        self.send_initial_event = send_initial_event
        self.on_open_callback = on_open_callback
        self.reconnect_interval = reconnect_interval
        self.websocket = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

    def on_open(self, ws):
        logger.info("Connected to simulation socket at %s", self.url)
        if self.send_initial_event:
            self.send_initial_event()
        if self.on_open_callback:
            self.on_open_callback()

    def on_error(self, ws, error):
        logger.error("Simulation socket error: %s", error, exc_info=True)

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(
            "Simulation socket closed (code=%s msg=%s)", close_status_code, close_msg
        )
        if self.reconnect_interval:
            logger.info(
                "Reconnecting in %s seconds...", self.reconnect_interval
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

    def send_message(self, message: str):
        try:
            self.websocket.send(message)
            logger.debug("Sent: %s", message)
        except Exception:
            logger.exception("Error sending message")
