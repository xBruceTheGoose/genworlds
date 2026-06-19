import json
import logging
import threading
import colorama

import websocket

logger = logging.getLogger(__name__)
colorama.init()


class TestClient:
    def __init__(self, url: str = "ws://127.0.0.1:7456/ws"):
        self.url = url
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

    def on_open(self, ws):
        thread_name = threading.current_thread().name
        logger.info("[%s] Connected to %s", thread_name, self.url)

    def on_message(self, ws, message):
        thread_name = threading.current_thread().name
        logger.info("[%s] Received: %s", thread_name, message)

    def on_error(self, ws, error):
        logger.error("TestClient error: %s", error)

    def on_close(self, ws, close_status_code, close_msg):
        logger.info("TestClient closed connection (code=%s)", close_status_code)

    def send_message(self, message: dict):
        msg = json.dumps(message)
        self.ws.send(msg)
        thread_name = threading.current_thread().name
        logger.info("[%s] Sent: %s", thread_name, msg)

    def run_forever(self):
        self.ws.run_forever()


def main():
    client = TestClient()
    thread = threading.Thread(
        target=client.run_forever, name="TestClient Thread", daemon=True
    )
    thread.start()
    thread.join()


if __name__ == "__main__":
    main()
