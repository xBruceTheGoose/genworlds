import os
from typing import List, Tuple

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from genworlds.agents.abstracts.agent_state import AbstractAgentState
from genworlds.agents.abstracts.thought import AbstractThought


class ActionSchemaSelectorThought(AbstractThought):
    def __init__(
        self,
        agent_state: AbstractAgentState,
        model_name: str = "gpt-4o-mini",
    ):
        self.agent_state = agent_state
        api_key = os.environ.get("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model=model_name, api_key=api_key, temperature=0.1)

    def run(self) -> Tuple[str, List[str]]:
        class PlanNextAction(BaseModel):
            """Plans for the next action to be executed by the agent."""

            action_name: str = Field(
                ...,
                description="Selects the action name of the next action to be executed from the list of available action names.",
            )
            is_action_valid: bool = Field(
                ..., description="Determines whether the next action is valid or not."
            )
            is_action_valid_reason: str = Field(
                ...,
                description="Then explains the rationale of whether it is valid or not valid action.",
            )
            new_plan: List[str] = Field(
                ..., description="The new plan to execute to achieve the goals."
            )

        action_schemas_full_string = "## Available Actions: \n\n"
        for key, value in self.agent_state.available_action_schemas.items():
            action_schemas_full_string += (
                "Action Name: "
                + key
                + "\nAction Description: "
                + value.split("|")[0]
                + "\n\n"
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are {agent_name}, {agent_description}.\n"),
                (
                    "system",
                    "You are embedded in a simulated world with those properties {agent_world_state}\n",
                ),
                ("system", "Those are your goals: \n{goals}\n"),
                (
                    "system",
                    "And this is the previous plan to achieve the goals: \n{plan}\n",
                ),
                (
                    "system",
                    "Here is your memories of all the events that you remember from being in this simulation: \n{memory}\n",
                ),
                (
                    "system",
                    "Those are the available actions that you can choose from: \n{available_actions}\n",
                ),
                ("human", "{footer}\n"),
            ]
        )

        structured_llm = self.llm.with_structured_output(PlanNextAction)
        chain = prompt | structured_llm

        response: PlanNextAction = chain.invoke(
            {
                "agent_name": self.agent_state.name,
                "agent_description": self.agent_state.description,
                "agent_world_state": self.agent_state.host_world_prompt,
                "goals": self.agent_state.goals,
                "plan": self.agent_state.plan,
                "memory": self.agent_state.last_retrieved_memory,
                "available_actions": action_schemas_full_string,
                "footer": (
                    "Select the next action which must be a value of the available actions "
                    "that you can choose from based on previous context.\n"
                    "Also select whether the action is valid or not, and if not, why.\n"
                    "And finally, state a new updated plan that you want to execute to achieve "
                    "your goals. If your next action is going to sleep, then you don't need to "
                    "state a new plan."
                ),
            }
        )
        return response.action_name, response.new_plan
