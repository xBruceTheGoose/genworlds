from __future__ import annotations
from uuid import uuid4
import threading
import logging
from typing import List
from genworlds.events.abstracts.action import AbstractAction
from genworlds.simulation.sockets.client import SimulationSocketClient
from genworlds.events.abstracts.event import AbstractEvent

logger = logging.getLogger(__name__)


class SimulationSocketEventHandler:
    def __init__(
        self,
        id: str,
        actions: List[AbstractAction] = [],
        external_event_classes: dict[str, AbstractEvent] = {},
        websocket_url: str = "ws://127.0.0.1:7456/ws",
    ):
        self.event_actions_dict: dict[str, list[AbstractAction]] = {}
        self.id = id if id else str(uuid4())
        self.actions = actions
        for action in self.actions:
            self.register_action(action)

        self.simulation_socket_client = SimulationSocketClient(
            process_event=self.process_event,
            url=websocket_url,
            on_open_callback=self._on_ws_open,
        )

    def _on_ws_open(self):
        """Signal readiness to any waiting threads (e.g., AbstractAgent.think_n_do)."""
        if hasattr(self, "_ws_ready"):
            self._ws_ready.set()

    def register_action(self, action: AbstractAction):
        event_type = action.trigger_event_class.model_fields["event_type"].default
        if event_type not in self.event_actions_dict:
            self.event_actions_dict[event_type] = []
        self.event_actions_dict[event_type].append(action)

    def process_event(self, event: dict):
        if event["event_type"] in self.event_actions_dict and (
            event["target_id"] is None or event["target_id"] == self.id
        ):
            try:
                parsed_event = self.event_actions_dict[event["event_type"]][
                    0
                ].trigger_event_class.model_validate(event)
                for listener in self.event_actions_dict[event["event_type"]]:
                    listener(parsed_event)
            except Exception:
                logger.exception(
                    "Error processing event '%s' for %s",
                    event.get("event_type"),
                    self.id,
                )

        if "*" in self.event_actions_dict:
            for listener in self.event_actions_dict["*"]:
                try:
                    listener(event)
                except Exception:
                    logger.exception("Error in wildcard listener for %s", self.id)

    def send_event(self, event: AbstractEvent):
        self.simulation_socket_client.send_message(event.model_dump_json())

    def launch_websocket_thread(self):
        threading.Thread(
            target=self.simulation_socket_client.websocket.run_forever,
            name=f"{self.id} Thread",
            daemon=True,
        ).start()
