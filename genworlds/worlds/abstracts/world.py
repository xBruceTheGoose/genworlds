from __future__ import annotations

import logging
import threading
from typing import Generic, TypeVar, List, Type

from genworlds.objects.abstracts.object import AbstractObject
from genworlds.worlds.abstracts.world_entity import AbstractWorldEntity
from genworlds.agents.abstracts.agent import AbstractAgent
from genworlds.events.abstracts.action import AbstractAction
from genworlds.simulation.sockets.server import start_thread as socket_server_start

logger = logging.getLogger(__name__)

WorldEntityType = TypeVar("WorldEntityType", bound=AbstractWorldEntity)


class AbstractWorld(Generic[WorldEntityType], AbstractObject):
    """An interface class representing a generic world in the simulation."""

    entities: dict[str, AbstractWorldEntity]
    action_schemas: dict[str, dict]
    _entity_lock: threading.RLock
    _schema_lock: threading.RLock

    def __init__(
        self,
        name: str,
        id: str,
        description: str,
        actions: List[Type[AbstractAction]],
        objects: List[AbstractObject],
        agents: List[AbstractAgent],
        get_available_entities: AbstractAction,
        get_available_action_schemas: AbstractAction,
    ):
        self.objects = objects
        self.agents = agents
        self.get_available_entities = get_available_entities
        self.get_available_action_schemas = get_available_action_schemas
        self.entities = {}
        self.action_schemas = {}
        self._entity_lock = threading.RLock()
        self._schema_lock = threading.RLock()
        super().__init__(
            name=name, id=id, description=description, host_world_id=id, actions=actions
        )

    def update_entities(self):
        with self._entity_lock:
            self.entities = {}
            self.entities[self.id] = self.get_entity_from_obj(self)
            for agent in self.agents:
                self.entities[agent.id] = self.get_entity_from_obj(agent)
            for obj in self.objects:
                self.entities[obj.id] = self.get_entity_from_obj(obj)

    def update_action_schemas(self):
        with self._schema_lock:
            self.action_schemas = {}
            for action in self.actions:
                key, value = action.action_schema
                self.action_schemas[key] = value
            for obj in self.objects:
                for action in obj.actions:
                    key, value = action.action_schema
                    self.action_schemas[key] = value
            for agent in self.agents:
                for action in agent.actions:
                    key, value = action.action_schema
                    self.action_schemas[key] = value

    def get_entity_from_obj(self, obj: AbstractObject) -> WorldEntityType:
        return AbstractWorldEntity.create(obj)

    def get_entity_by_id(self, entity_id: str) -> WorldEntityType:
        return self.entities[entity_id]

    def add_agent(self, agent: AbstractAgent):
        agent.host_world_id = self.id
        self.agents.append(agent)
        agent.launch()

    def add_object(self, obj: AbstractObject):
        obj.host_world_id = self.id
        self.objects.append(obj)
        obj.launch_websocket_thread()

    def launch(self, host: str = "127.0.0.1", port: int = 7456):
        """
        Start the WebSocket server, connect the world, then connect each
        agent and object in order — waiting for each WS connection before
        proceeding to avoid the old sleep-based race.
        """
        server_ready = threading.Event()

        def _server_ready_probe():
            import time as _time
            for _ in range(50):
                try:
                    import websocket as _ws
                    ws = _ws.create_connection(f"ws://{host}:{port}/ws")
                    ws.close()
                    server_ready.set()
                    return
                except Exception:
                    _time.sleep(0.1)
            logger.error("WebSocket server did not become ready in time.")

        socket_server_start(host=host, port=port)
        threading.Thread(target=_server_ready_probe, daemon=True).start()
        server_ready.wait(timeout=10)

        self.launch_websocket_thread()
        self._ws_ready.wait(timeout=10)

        for agent in list(self.agents):
            self.add_agent(agent)
            agent._ws_ready.wait(timeout=10)

        for obj in list(self.objects):
            self.add_object(obj)
