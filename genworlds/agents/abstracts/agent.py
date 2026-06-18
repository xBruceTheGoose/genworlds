import logging
import traceback
import threading
from typing import List, Type

from genworlds.agents.abstracts.action_planner import AbstractActionPlanner
from genworlds.agents.abstracts.state_manager import AbstractStateManager
from genworlds.events.abstracts.action import AbstractAction
from genworlds.objects.abstracts.object import AbstractObject

logger = logging.getLogger(__name__)


class AbstractAgent(AbstractObject):
    """Abstract interface class for an Agent."""

    def __init__(
        self,
        name: str,
        id: str,
        description: str,
        state_manager: AbstractStateManager,
        action_planner: AbstractActionPlanner,
        host_world_id: str = None,
        actions: List[Type[AbstractAction]] = [],
    ):
        self.action_planner = action_planner
        self.state_manager = state_manager
        self._ws_ready = threading.Event()
        super().__init__(name, id, description, host_world_id, actions)

    def think_n_do(self):
        """Continuously plans and executes actions based on the agent's state."""
        self._ws_ready.wait()
        while True:
            try:
                if self.state_manager.state.is_asleep:
                    threading.Event().wait(timeout=1.0)
                    continue

                state = self.state_manager.get_updated_state()
                action_schema, trigger_event = self.action_planner.plan_next_action(state)

                if action_schema.startswith(self.id):
                    # O(1) dispatch via the pre-built event_actions_dict
                    action_key = action_schema.split(":", 1)[1] if ":" in action_schema else action_schema
                    selected = next(
                        (
                            a
                            for a in self.actions
                            if a.action_schema[0] == action_schema
                        ),
                        None,
                    )
                    if selected is None:
                        logger.warning("No action found for schema '%s'", action_schema)
                        continue
                    selected(trigger_event)
                else:
                    self.send_event(trigger_event)
            except Exception:
                logger.exception("Error in think_n_do for agent %s", self.id)

    def launch(self):
        """Launches the agent by starting the websocket and thinking threads."""
        self.launch_websocket_thread()
        thinking_thread = threading.Thread(
            target=self.think_n_do,
            name=f"Agent {self.id} Thinking Thread",
            daemon=True,
        )
        thinking_thread.start()
