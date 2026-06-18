"""
RoundtableAgent — migrated to BasicAssistant.

The original RoundtableAgent was built on top of the now-removed
`genworlds.agents.base_agent` module.  To rebuild it, create a
BasicAssistant subclass with the podcast-specific thoughts wired in
as `other_thoughts`.

Example (sketch):

    from genworlds.agents.concrete.basic_assistant.agent import BasicAssistant
    from use_cases.roundtable.thoughts.podcast_thought import PodcastThought

    class RoundtableAgent(BasicAssistant):
        def __init__(self, name, id, role, background, ...):
            initial_state = AbstractAgentState(
                name=name,
                id=id,
                description=f"{role}. {background}",
                goals=[...],
                ...
            )
            super().__init__(
                name=name,
                id=id,
                description=f"{role}. {background}",
                initial_agent_state=initial_state,
                other_thoughts=[PodcastThought(...)],
                ...
            )
"""
from genworlds.agents.concrete.basic_assistant.agent import BasicAssistant as RoundtableAgent  # noqa: F401
