"""
EventFillerThought for roundtable — stub pending migration.

The original implementation depended on the removed
`genworlds.agents.base_agent.thoughts.SingleEvalThoughtGenerator`.
Use `genworlds.agents.concrete.basic_assistant.thoughts.EventFillerThought`
as the replacement base class.
"""
from genworlds.agents.concrete.basic_assistant.thoughts.event_filler import (
    EventFillerThought,  # noqa: F401
)
