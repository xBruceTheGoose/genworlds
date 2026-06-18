from typing import List
from genworlds.agents.abstracts.agent import AbstractAgent
from genworlds.events.abstracts.event import AbstractEvent
from genworlds.agents.abstracts.agent_state import AbstractAgentState
from genworlds.agents.concrete.basic_assistant.state_manager import (
    BasicAssistantStateManager,
)
from genworlds.agents.concrete.basic_assistant.action_planner import (
    BasicAssistantActionPlanner,
)
from genworlds.events.abstracts.action import AbstractAction
from genworlds.agents.concrete.basic_assistant.actions import (
    UpdateAgentAvailableEntities,
    UpdateAgentAvailableActionSchemas,
    AgentGoesToSleep,
    AgentListensEvents,
    AgentSpeaksWithUser,
    AgentSpeaksWithAgent,
)
from genworlds.agents.abstracts.thought import AbstractThought


class BasicAssistant(AbstractAgent):
    def __init__(
        self,
        name: str,
        id: str,
        description: str,
        host_world_id: str = None,
        initial_agent_state: AbstractAgentState = None,
        action_classes: List[type[AbstractAction]] = [],
        other_thoughts: List[AbstractThought] = [],
        model_name: str = "gpt-4o-mini",
    ):
        state_manager = BasicAssistantStateManager(self, initial_agent_state)
        action_planner = BasicAssistantActionPlanner(
            initial_agent_state=state_manager.state,
            other_thoughts=other_thoughts,
            model_name=model_name,
            host_agent=self,
        )

        actions = [action_class(host_object=self) for action_class in action_classes]
        actions.append(UpdateAgentAvailableEntities(host_object=self))
        actions.append(UpdateAgentAvailableActionSchemas(host_object=self))
        actions.append(AgentGoesToSleep(host_object=self))
        actions.append(AgentListensEvents(host_object=self))
        actions.append(AgentSpeaksWithUser(host_object=self))
        actions.append(AgentSpeaksWithAgent(host_object=self))

        super().__init__(
            name, id, description, state_manager, action_planner, host_world_id, actions
        )

    def add_wakeup_event(self, event_class: AbstractEvent):
        event_type = event_class.model_fields["event_type"].default
        self.state_manager.state.wakeup_event_types.add(event_type)

    def add_memory_ignored_event(self, event_type: str):
        self.state_manager.state.memory_ignored_event_types.add(event_type)
