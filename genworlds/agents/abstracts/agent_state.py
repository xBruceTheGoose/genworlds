from typing import Dict, List, Set, Any, Optional
from pydantic import BaseModel, Field


class AbstractAgentState(BaseModel):
    # Static: set at construction time
    id: str = Field(..., description="Unique identifier of the agent.")
    description: str = Field(..., description="Description of the agent.")
    name: str = Field(..., description="Name of the agent.")
    host_world_prompt: str = Field(..., description="Prompt of the host world.")
    simulation_memory_persistent_path: Optional[str] = Field(
        None, description="Memory object storing the simulation data."
    )
    memory_ignored_event_types: Set[str] = Field(
        default_factory=set,
        description="Event types that will not be added to agent memory.",
    )
    wakeup_event_types: Set[str] = Field(
        default_factory=set,
        description="Events that can wake up the agent.",
    )
    action_schema_chains: List[List[str]] = Field(
        default_factory=list,
        description="Action schema chains that inhibit the action selector.",
    )
    goals: List[str] = Field(..., description="List of goals of the agent.")

    # Dynamic: updated each think cycle
    plan: List[str] = Field(default_factory=list, description="Current plan.")
    last_retrieved_memory: str = Field(
        default="", description="Last retrieved memory of the agent."
    )
    other_thoughts_filled_parameters: Dict[str, str] = Field(
        default_factory=dict,
        description="Parameters filled by other thoughts.",
    )
    available_action_schemas: Dict[str, Any] = Field(
        default_factory=dict,
        description="Available action schemas with their descriptions.",
    )
    available_entities: List[str] = Field(
        default_factory=list,
        description="List of available entities in the environment.",
    )
    is_asleep: bool = Field(default=False, description="Whether the agent is asleep.")
    current_action_chain: List[str] = Field(
        default_factory=list,
        description="Action schemas currently being executed in sequence.",
    )
