"""
PodcastThought — pending migration to the new AbstractThought API.

The original implementation depended on the removed
`genworlds.agents.base_agent.thoughts.SingleEvalThoughtGenerator`
and `genworlds.agents.base_agent.prompts.ExecutionGeneratorPrompt`.

To migrate, subclass AbstractThought and implement run():

    from genworlds.agents.abstracts.thought import AbstractThought
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    class PodcastThought(AbstractThought):
        def __init__(self, name, role, ...):
            self.llm = ChatOpenAI(model="gpt-4o-mini")
            ...

        def run(self, *args, **kwargs):
            chain = self._prompt | self.llm
            return chain.invoke({...})
"""
from genworlds.agents.abstracts.thought import AbstractThought


class PodcastThought(AbstractThought):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "PodcastThought must be reimplemented using AbstractThought. "
            "See the module docstring for the migration guide."
        )

    def run(self, *args, **kwargs):
        raise NotImplementedError
