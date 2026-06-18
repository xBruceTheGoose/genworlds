from __future__ import annotations

import logging
import threading
from uuid import uuid4
from typing import List

from genworlds.objects.abstracts.object import AbstractObject
from genworlds.agents.abstracts.agent import AbstractAgent
from genworlds.worlds.abstracts.world import AbstractWorld

logger = logging.getLogger(__name__)


class Simulation:
    def __init__(
        self,
        name: str,
        description: str,
        world: AbstractWorld,
        objects: List[AbstractObject] = None,
        agents: List[AbstractAgent] = None,
        stop_event: threading.Event = None,
    ):
        self.id = str(uuid4())
        self.name = name
        self.description = description
        self.world = world
        self.stop_event = stop_event

        # Add any agents/objects provided at construction time into the world
        for obj in objects or []:
            obj.host_world_id = world.id
            if obj not in world.objects:
                world.objects.append(obj)

        for agent in agents or []:
            agent.host_world_id = world.id
            if agent not in world.agents:
                world.agents.append(agent)

    def add_agent(self, agent: AbstractAgent):
        self.world.add_agent(agent)

    def add_object(self, obj: AbstractObject):
        self.world.add_object(obj)

    def launch(self, host: str = "127.0.0.1", port: int = 7456):
        """
        Launch the full simulation.  The world is responsible for starting the
        WebSocket server and synchronising agent/object startup.
        """
        self.world.launch(host=host, port=port)
        logger.info("Simulation '%s' (%s) running.", self.name, self.id)

        while True:
            if self.stop_event and self.stop_event.is_set():
                logger.info("Stop event set — shutting down simulation.")
                break
            try:
                threading.Event().wait(timeout=1.0)
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt — shutting down simulation.")
                break
