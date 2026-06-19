from __future__ import annotations

import logging
import signal
import threading
from uuid import uuid4
from typing import List, Optional

from genworlds.objects.abstracts.object import AbstractObject
from genworlds.agents.abstracts.agent import AbstractAgent
from genworlds.worlds.abstracts.world import AbstractWorld
from genworlds.simulation.config import get_config, SimulationConfig

logger = logging.getLogger(__name__)


class Simulation:
    """Orchestrates a GenWorlds simulation lifecycle.

    A simulation manages a world, its agents, objects, and the WebSocket
    communication infrastructure. It provides methods to launch, monitor,
    and gracefully shutdown the simulation.

    Attributes:
        id: Unique identifier for this simulation instance
        name: Human-readable name
        description: Description of the simulation purpose
        world: The world instance being simulated
        stop_event: Threading event for coordinated shutdown

    Example:
        >>> from genworlds.simulation import Simulation
        >>> sim = Simulation("MySim", "Description", world=my_world)
        >>> sim.launch()
    """

    def __init__(
        self,
        name: str,
        description: str,
        world: AbstractWorld,
        objects: Optional[List[AbstractObject]] = None,
        agents: Optional[List[AbstractAgent]] = None,
        stop_event: Optional[threading.Event] = None,
        config: Optional[SimulationConfig] = None,
    ):
        self.id = str(uuid4())
        self.name = name
        self.description = description
        self.world = world
        self.stop_event = stop_event or threading.Event()
        self.config = config or get_config()
        self._shutting_down = False

        for obj in objects or []:
            obj.host_world_id = world.id
            if obj not in world.objects:
                world.objects.append(obj)

        for agent in agents or []:
            agent.host_world_id = world.id
            if agent not in world.agents:
                world.agents.append(agent)

    def add_agent(self, agent: AbstractAgent) -> None:
        """Add an agent to the simulation world."""
        self.world.add_agent(agent)

    def add_object(self, obj: AbstractObject) -> None:
        """Add an object to the simulation world."""
        self.world.add_object(obj)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            if self._shutting_down:
                return
            self._shutting_down = True
            logger.info("Received signal %d, initiating graceful shutdown", signum)
            self.stop_event.set()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def launch(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        """Launch the full simulation.

        The world is responsible for starting the WebSocket server and
        synchronizing agent/object startup. Uses configuration defaults
        if host/port not specified.

        Args:
            host: WebSocket server host (default from config)
            port: WebSocket server port (default from config)
        """
        host = host or self.config.websocket_host
        port = port or self.config.websocket_port

        self._setup_signal_handlers()

        self.world.launch(host=host, port=port)
        logger.info("Simulation '%s' (%s) running on %s:%d", self.name, self.id, host, port)

        while not self.stop_event.is_set():
            try:
                self.stop_event.wait(timeout=1.0)
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt — shutting down simulation.")
                break

        self._shutdown()

    def _shutdown(self) -> None:
        """Perform graceful shutdown of all components."""
        logger.info("Shutting down simulation '%s'", self.name)

        if hasattr(self.world, 'shutdown'):
            for agent in self.world.agents:
                if hasattr(agent, 'shutdown'):
                    try:
                        agent.shutdown()
                    except Exception as e:
                        logger.warning("Error shutting down agent %s: %s", agent.id, e)

        logger.info("Simulation '%s' shutdown complete", self.name)

    def stop(self) -> None:
        """Request simulation stop from external caller."""
        logger.info("External stop requested for simulation '%s'", self.name)
        self.stop_event.set()
