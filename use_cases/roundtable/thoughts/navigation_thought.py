"""
NavigationThought for roundtable — stub pending migration.

The original implementation depended on the removed
`genworlds.agents.base_agent.thoughts.SingleEvalThoughtGenerator`.
Use `genworlds.agents.concrete.basic_assistant.thoughts.ActionSchemaSelectorThought`
as the replacement base class for navigation/action selection logic.
"""
from genworlds.agents.concrete.basic_assistant.thoughts.action_schema_selector import (
    ActionSchemaSelectorThought as NavigationThought,  # noqa: F401
)
