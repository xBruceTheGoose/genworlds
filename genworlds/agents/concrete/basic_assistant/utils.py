from typing import List, Optional
from uuid import uuid4

from genworlds.agents.abstracts.thought import AbstractThought
from genworlds.events.abstracts.action import AbstractAction
from genworlds.agents.concrete.basic_assistant.agent import BasicAssistant
from genworlds.agents.abstracts.agent_state import AbstractAgentState


def generate_basic_assistant(
    agent_name: str,
    description: str,
    host_world_id: Optional[str] = None,
    initial_agent_state: Optional[AbstractAgentState] = None,
    other_thoughts: List[AbstractThought] = [],
    model_name: str = "gpt-4o-mini",
    action_classes: List[type[AbstractAction]] = [],
    action_schema_chains: List[List[str]] = [],
    simulation_memory_persistent_path: str = "./",
) -> BasicAssistant:
    """Factory for simple single-world assistant agents."""
    agent_id = agent_name or str(uuid4())

    if not initial_agent_state:
        initial_agent_state = AbstractAgentState(
            name=agent_name,
            id=agent_id,
            description=description,
            goals=[
                "Wait until the user starts a new question.",
                f"Once {agent_name} receives a user's question, make sure to gather all information before answering.",
                f"When {agent_name} has all required information, speak to the user with results via agent_speaks_with_user_event.",
                "After sending the response, wait for the next user question.",
                "If waiting for any entity for over 30 seconds, go to sleep until a new event arrives.",
            ],
            available_entities={},
            available_action_schemas={},
            current_action_chain=[],
            host_world_prompt="",
            simulation_memory_persistent_path=simulation_memory_persistent_path,
            memory_ignored_event_types={
                "world_sends_available_action_schemas_event",
                "world_sends_available_entities_event",
                "agent_wants_updated_state",
            },
            wakeup_event_types=set(),
            is_asleep=False,
            action_schema_chains=action_schema_chains,
        )

    return BasicAssistant(
        name=agent_name,
        id=agent_id,
        description=description,
        host_world_id=host_world_id,
        initial_agent_state=initial_agent_state,
        action_classes=action_classes,
        other_thoughts=other_thoughts,
        model_name=model_name,
    )
