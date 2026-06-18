from genworlds.agents.abstracts.state_manager import AbstractStateManager
from genworlds.agents.abstracts.agent_state import AbstractAgentState
from genworlds.agents.abstracts.agent import AbstractAgent

from genworlds.worlds.concrete.base.actions import AgentWantsUpdatedStateEvent
from genworlds.agents.memories.simulation_memory import SimulationMemory


class BasicAssistantStateManager(AbstractStateManager):
    """Keeps track of the current state of the agent."""

    def __init__(
        self,
        host_agent: AbstractAgent,
        state: AbstractAgentState = None,
        model_name: str = "gpt-4o-mini",
    ):
        self.host_agent = host_agent
        self.state = state if state else self._initialize_state()
        self.memory = SimulationMemory(model_name=model_name)

    def _initialize_state(self) -> AbstractAgentState:
        return AbstractAgentState(
            name=self.host_agent.name,
            id=self.host_agent.id,
            description=self.host_agent.description,
            goals=[
                "Wait until the user starts a new question.",
                f"Once {self.host_agent.name} receives a user's question, make sure to gather all information before answering.",
                f"When {self.host_agent.name} has all required information, speak to the user with results via agent_speaks_with_user_event.",
                "After sending the response, wait for the next user question.",
                "If waiting for any entity for over 30 seconds, go to sleep until a new event arrives.",
            ],
            available_entities={},
            available_action_schemas={},
            current_action_chain=[],
            host_world_prompt="",
            is_asleep=False,
            simulation_memory_persistent_path="./",
            wakeup_event_types=set(),
            action_schema_chains=[],
        )

    def get_updated_state(self) -> AbstractAgentState:
        self.host_agent.send_event(
            AgentWantsUpdatedStateEvent(
                sender_id=self.host_agent.id,
                target_id=self.host_agent.host_world_id,
            )
        )
        query = "No plan" if not self.state.plan else str(self.state.plan)
        self.state.last_retrieved_memory = (
            self.memory.get_event_stream_memories(query=query)
        )
        return self.state
