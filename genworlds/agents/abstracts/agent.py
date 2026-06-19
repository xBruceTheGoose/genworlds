import logging
import threading
from typing import List, Type, Optional

from genworlds.agents.abstracts.action_planner import AbstractActionPlanner
from genworlds.agents.abstracts.state_manager import AbstractStateManager
from genworlds.events.abstracts.action import AbstractAction
from genworlds.objects.abstracts.object import AbstractObject

logger = logging.getLogger(__name__)


class AgentException(Exception):
    """Raised when agent encounters an unrecoverable error."""
    pass


class AbstractAgent(AbstractObject):
    """Abstract interface class for an Agent.

    An agent is an autonomous entity that perceives its environment through
    events and acts upon it through actions. The main cognitive loop runs in
    a separate thread and orchestrates action planning and execution.

    Attributes:
        action_planner: The planner responsible for selecting and parameterizing actions
        state_manager: Manages the agent's internal state
        _ws_ready: Event signalling when WebSocket connection is established

    Example:
        >>> class MyAgent(AbstractAgent):
        ...     def __init__(self, name, id):
        ...         super().__init__(
        ...             name=name, id=id, description="My agent",
        ...             state_manager=StateManager(),
        ...             action_planner=ActionPlanner()
        ...         )
    """

    def __init__(
        self,
        name: str,
        id: str,
        description: str,
        state_manager: AbstractStateManager,
        action_planner: AbstractActionPlanner,
        host_world_id: Optional[str] = None,
        actions: Optional[List[Type[AbstractAction]]] = None,
    ):
        self.action_planner = action_planner
        self.state_manager = state_manager
        self._ws_ready = threading.Event()
        self._shutdown = threading.Event()
        self._error_count = 0
        self._max_consecutive_errors = 10
        actions = actions or []
        super().__init__(name, id, description, host_world_id, actions)

    def think_n_do(self) -> None:
        """Continuously plan and execute actions based on agent state.

        This is the main cognitive loop that runs in a separate thread.
        It waits for WebSocket connection, then cycles through action
        planning and execution until shutdown or unrecoverable error.
        """
        logger.info("Agent %s waiting for WebSocket connection", self.id)
        if not self._ws_ready.wait(timeout=30.0):
            logger.error("Agent %s failed to connect within timeout", self.id)
            return

        logger.info("Agent %s starting cognitive loop", self.id)
        while not self._shutdown.is_set():
            try:
                if self.state_manager.state.is_asleep:
                    self._shutdown.wait(timeout=1.0)
                    continue

                state = self.state_manager.get_updated_state()
                action_schema, trigger_event = self.action_planner.plan_next_action(state)

                if action_schema.startswith(self.id):
                    action_key = action_schema.split(":", 1)[1] if ":" in action_schema else action_schema
                    selected = next(
                        (a for a in self.actions if a.action_schema[0] == action_schema),
                        None,
                    )
                    if selected is None:
                        logger.warning(
                            "Agent %s: No action found for schema '%s'",
                            self.id,
                            action_schema,
                        )
                        continue
                    logger.debug("Agent %s executing action: %s", self.id, action_schema)
                    selected(trigger_event)
                    self._error_count = 0
                else:
                    logger.debug("Agent %s sending event: %s", self.id, action_schema)
                    self.send_event(trigger_event)
                    self._error_count = 0

            except Exception as e:
                self._error_count += 1
                logger.exception(
                    "Agent %s error in cognitive loop (count=%d/%d): %s",
                    self.id,
                    self._error_count,
                    self._max_consecutive_errors,
                    e,
                )
                if self._error_count >= self._max_consecutive_errors:
                    logger.critical(
                        "Agent %s exceeded max consecutive errors, stopping",
                        self.id,
                    )
                    self._shutdown.set()

    def launch(self) -> None:
        """Launch the agent by starting WebSocket and cognitive loop threads."""
        logger.info("Launching agent %s (%s)", self.id, self.name)
        self.launch_websocket_thread()
        thinking_thread = threading.Thread(
            target=self.think_n_do,
            name=f"Agent {self.id} Thinking Thread",
            daemon=True,
        )
        thinking_thread.start()

    def shutdown(self) -> None:
        """Gracefully shutdown the agent."""
        logger.info("Shutting down agent %s", self.id)
        self._shutdown.set()
        self.simulation_socket_client.close()
