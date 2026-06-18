from typing import List, Dict, Any, Optional
from genworlds.agents.abstracts.agent import AbstractAgent
from genworlds.agents.abstracts.agent_state import AbstractAgentState
from genworlds.agents.abstracts.action_planner import AbstractActionPlanner
from genworlds.agents.abstracts.thought import AbstractThought
from genworlds.agents.concrete.basic_assistant.thoughts.action_schema_selector import (
    ActionSchemaSelectorThought,
)
from genworlds.agents.concrete.basic_assistant.thoughts.event_filler import (
    EventFillerThought,
)
from genworlds.agents.abstracts.thought_action import ThoughtAction
from genworlds.utils.schema_to_model import json_schema_to_pydantic_model
from genworlds.events.abstracts.event import AbstractEvent
import json


class BasicAssistantActionPlanner(AbstractActionPlanner):
    def __init__(
        self,
        host_agent: AbstractAgent,
        initial_agent_state: AbstractAgentState,
        other_thoughts: List[AbstractThought] = [],
        model_name: str = "gpt-4o-mini",
    ):
        self.host_agent = host_agent
        action_schema_selector = ActionSchemaSelectorThought(
            agent_state=initial_agent_state,
            model_name=model_name,
        )
        event_filler = EventFillerThought(
            agent_state=initial_agent_state,
            model_name=model_name,
        )
        super().__init__(action_schema_selector, event_filler, other_thoughts)

    def select_next_action_schema(self, state: AbstractAgentState) -> str:
        next_action_schema, updated_plan = self.action_schema_selector.run()
        state.plan = updated_plan
        if next_action_schema in [el[0] for el in state.action_schema_chains]:
            state.current_action_chain = state.action_schema_chains[
                [el[0] for el in state.action_schema_chains].index(next_action_schema)
            ][1:]
        return next_action_schema

    def fill_triggering_event(
        self, next_action_schema: str, state: AbstractAgentState
    ) -> AbstractEvent:
        if next_action_schema.startswith(self.host_agent.id):
            selected = next(
                (
                    a
                    for a in self.host_agent.actions
                    if a.action_schema[0] == next_action_schema
                ),
                None,
            )
            if selected is None:
                raise ValueError(f"No action found for schema '{next_action_schema}'")
            trigger_event_class = selected.trigger_event_class
            if isinstance(selected, ThoughtAction):
                for param, thought_class in selected.required_thoughts.items():
                    thought = thought_class(self.host_agent.state_manager.state)
                    state.other_thoughts_filled_parameters[param] = thought.run()
        else:
            raw = self.host_agent.state_manager.state.available_action_schemas.get(
                next_action_schema
            )
            if raw is None:
                raise ValueError(
                    f"Action schema '{next_action_schema}' not found in available schemas."
                )
            trigger_event_class = json_schema_to_pydantic_model(
                json.loads(raw.split("|")[-1])
            )

        trigger_event: AbstractEvent = self.event_filler.run(trigger_event_class)
        return trigger_event
