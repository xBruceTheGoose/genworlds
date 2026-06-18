import json
import os
import logging
from typing import List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import qdrant_client
from qdrant_client.http import models as rest
from langchain_community.vectorstores import Qdrant
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class OneLineEventSummarizer:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.summary_prompt = PromptTemplate(
            template=(
                "This is the last event coming from a web-socket, it is in JSON format:\n"
                "{event}\n"
                "Summarize what happened in one line."
            ),
            input_variables=["event"],
        )
        api_key = os.environ.get("OPENAI_API_KEY")
        self.chat = ChatOpenAI(temperature=0, model=model_name, api_key=api_key)
        self.chain = self.summary_prompt | self.chat | StrOutputParser()

    def summarize(self, event: str) -> str:
        return self.chain.invoke({"event": event})


class FullEventStreamSummarizer:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.summary_prompt = PromptTemplate(
            template=(
                "This is the full event stream coming from a web-socket, it is in JSON format:\n"
                "{event_stream}\n"
                "Summarize what happened during the event stream in {k} paragraphs.\n\n"
                "SUMMARY:"
            ),
            input_variables=["event_stream", "k"],
        )
        api_key = os.environ.get("OPENAI_API_KEY")
        self.chat = ChatOpenAI(temperature=0, model=model_name, api_key=api_key)
        self.chain = self.summary_prompt | self.chat | StrOutputParser()

    def summarize(self, event_stream: List[str], k: int = 5) -> str:
        if not event_stream:
            return ""

        # For streams longer than 100, chunk and recursively summarize
        if len(event_stream) > 100:
            chunk_size = 50
            chunk_summaries: List[str] = []
            for i in range(0, len(event_stream), chunk_size):
                chunk = event_stream[i : i + chunk_size]
                chunk_summary = self.chain.invoke(
                    {"event_stream": "\n".join(chunk), "k": 2}
                )
                chunk_summaries.append(chunk_summary)
            return self.chain.invoke(
                {"event_stream": "\n".join(chunk_summaries), "k": k}
            )

        return self.chain.invoke({"event_stream": "\n".join(event_stream), "k": k})


class SimulationMemory:
    """
    Uses NMK Approach (N last events, M similar events, K-paragraph summary) to build agent memory.
    """

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        n_of_last_events: int = 15,
        n_of_similar_events: int = 5,
        n_of_paragraphs_in_summary: int = 5,
        batch_size: int = 10,
    ):
        self.n_of_last_events = n_of_last_events
        self.n_of_similar_events = n_of_similar_events
        self.n_of_paragraphs_in_summary = n_of_paragraphs_in_summary
        self.batch_size = batch_size
        self.full_summary = ""

        self.world_events: List[str] = []
        self.summarized_events: List[str] = []
        self._pending_docs: List[Document] = []

        api_key = os.environ.get("OPENAI_API_KEY")
        self.one_line_summarizer = OneLineEventSummarizer(model_name=model_name)
        self.full_event_stream_summarizer = FullEventStreamSummarizer(model_name=model_name)
        self.embeddings_model = OpenAIEmbeddings(api_key=api_key)

        client = qdrant_client.QdrantClient(location=":memory:")
        for collection_name in ("world-events", "summarized-world-events"):
            client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "content": rest.VectorParams(
                        distance=rest.Distance.COSINE,
                        size=1536,
                    ),
                },
            )
        self.events_db = Qdrant(
            client=client,
            collection_name="world-events",
            embeddings=self.embeddings_model,
        )
        self.summarized_events_db = Qdrant(
            client=client,
            collection_name="summarized-world-events",
            embeddings=self.embeddings_model,
        )

    def add_event(self, event: str, summarize: bool = False) -> None:
        self.world_events.append(event)
        self._pending_docs.append(Document(page_content=event))
        if len(self._pending_docs) >= self.batch_size:
            self._flush_pending_docs()
        if summarize:
            self._add_summarized_event(event)

    def _flush_pending_docs(self) -> None:
        if not self._pending_docs:
            return
        try:
            self.events_db.add_documents(self._pending_docs)
        except Exception:
            logger.exception("Failed to flush %d events to vector store", len(self._pending_docs))
        self._pending_docs = []

    def _add_summarized_event(self, event: str) -> None:
        sum_event = self.one_line_summarizer.summarize(event)
        event_as_dict = json.loads(event)
        self.summarized_events.append(event_as_dict["created_at"] + " " + sum_event)
        self.summarized_events_db.add_documents([Document(page_content=sum_event)])

    def create_full_summary(self) -> None:
        self.full_summary = self.full_event_stream_summarizer.summarize(
            event_stream=self.world_events, k=self.n_of_paragraphs_in_summary
        )

    def _get_n_last_events(self, summarized: bool = False) -> List[str]:
        events = self.summarized_events if summarized else self.world_events
        return events[-self.n_of_last_events :]

    def _get_m_similar_events(self, query: str, summarized: bool = False) -> List[str]:
        if self.n_of_similar_events < 1:
            return []
        db = self.summarized_events_db if summarized else self.events_db
        # Flush pending writes so similarity search sees current events
        self._flush_pending_docs()
        try:
            results = db.similarity_search(k=self.n_of_similar_events, query=query)
            return [el.page_content for el in results]
        except Exception:
            logger.exception("Similarity search failed")
            return []

    def get_event_stream_memories(self, query: str, summarized: bool = False) -> str:
        last_events = self._get_n_last_events(summarized=summarized)

        if len(self.world_events) <= self.n_of_last_events:
            return (
                "\n\n# Your Memories\n\n"
                "## Last events from oldest to most recent\n\n"
                + "\n".join(last_events)
            )

        similar_events = self._get_m_similar_events(query=query, summarized=summarized)
        return (
            "\n\n# Your Memories\n\n"
            "## Full Summary\n\n"
            + self.full_summary
            + "\n\n## Similar events\n\n"
            + "\n".join(similar_events)
            + "\n\n## Last events from oldest to most recent\n\n"
            + "\n".join(last_events)
        )
