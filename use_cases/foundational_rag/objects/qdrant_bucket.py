import os
import json
import logging
import threading
from json import JSONDecodeError
from typing import List

from qdrant_client import QdrantClient
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.vectorstores import Qdrant
from langchain_core.documents import Document
from langchain.text_splitter import CharacterTextSplitter, TokenTextSplitter

from genworlds.objects.abstracts.object import AbstractObject
from genworlds.events.abstracts.event import AbstractEvent
from genworlds.events.abstracts.action import AbstractAction

logger = logging.getLogger(__name__)

_NER_SYSTEM_PROMPT = """
Task:

Extract the named entities and their descriptions from the provided text.
An entity in this context refers to a term, concept, or organization that
has an explicit explanation or definition in the text.

Process:

1. Identify distinct named entities in the text.
2. Extract the corresponding explanation or definition for each entity.
3. Present entities in the format {"Entities": [{"Entity1": "desc1"}, ...]}.
4. Verify the dict can be loaded with json.loads().
5. If no explained entities are identified, state "NO ENTITIES EXPLAINED".

Text:

"""


class VectorStoreCollectionCreated(AbstractEvent):
    event_type: str = "vector_store_collection_created"
    description: str = "Notifies that a new collection has been created."
    has_been_created: bool = False
    collection_name: str
    sender_id: str


class VectorStoreCollectionCreationInProcess(AbstractEvent):
    event_type: str = "vector_store_collection_creation_in_process"
    description: str = "Notifies that collection creation is ongoing."
    collection_name: str
    sender_id: str


class AgentGeneratesTextChunkCollection(AbstractEvent):
    event_type: str = "agent_generates_text_chunk_collection"
    description: str = "Agent needs to generate a collection of text chunks for Qdrant."
    full_text_path: str
    collection_name: str
    num_tokens_chunk_size: int = 500
    metadata: dict = {}
    sender_id: str


class GenerateTextChunkCollection(AbstractAction):
    trigger_event_class = AgentGeneratesTextChunkCollection
    description = "Generate a collection of text chunks for storage in Qdrant."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentGeneratesTextChunkCollection):
        threading.Thread(
            target=self._run, args=(event,), daemon=True
        ).start()

    def _run(self, event: AgentGeneratesTextChunkCollection):
        self.host_object.send_event(
            VectorStoreCollectionCreationInProcess(
                sender_id=self.host_object.id,
                target_id=event.sender_id,
                collection_name=event.collection_name,
            )
        )
        text_splitter = TokenTextSplitter(
            chunk_size=event.num_tokens_chunk_size, chunk_overlap=0
        )
        with open(event.full_text_path, "r") as f:
            joint_text = f.read()

        texts = text_splitter.split_text(joint_text)
        docs = [Document(page_content=t) for t in texts]
        embeddings = OpenAIEmbeddings()
        Qdrant.from_documents(
            docs,
            embeddings,
            path=self.host_object.path,
            collection_name=event.collection_name,
        )
        logger.info(
            "Agent %s created collection '%s'.", event.sender_id, event.collection_name
        )
        self.host_object.send_event(
            VectorStoreCollectionCreated(
                sender_id=self.host_object.id,
                target_id=event.sender_id,
                collection_name=event.collection_name,
                has_been_created=True,
            )
        )


class AgentGeneratesNERCollection(AbstractEvent):
    event_type: str = "agent_generates_ner_collection"
    description: str = "Agent generates a named entity collection from a text."
    full_text_path: str
    collection_name: str
    num_tokens_chunk_size: int = 500
    metadata: dict = {}
    sender_id: str


class GenerateNERCollection(AbstractAction):
    trigger_event_class = AgentGeneratesNERCollection
    description = "Generate a named entity recognition collection for storage in Qdrant."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentGeneratesNERCollection):
        threading.Thread(target=self._run, args=(event,), daemon=True).start()

    def _run(self, event: AgentGeneratesNERCollection):
        self.host_object.is_busy = True
        self.host_object.send_event(
            VectorStoreCollectionCreationInProcess(
                sender_id=self.host_object.id,
                target_id=event.sender_id,
                collection_name=event.collection_name,
            )
        )
        chat = ChatOpenAI(model="gpt-4o-mini")
        sys_msg = SystemMessage(content=_NER_SYSTEM_PROMPT)

        with open(event.full_text_path, "r") as f:
            joint_text = f.read()

        text_splitter = TokenTextSplitter(chunk_size=1000, chunk_overlap=0)
        chunks = [
            Document(page_content=t)
            for t in text_splitter.split_text(joint_text)
        ]

        concepts: List[dict] = []
        for i, chunk in enumerate(chunks):
            for attempt in range(10):
                reply = chat.invoke([sys_msg, HumanMessage(content=chunk.page_content)])
                if "NO ENTITIES EXPLAINED" in reply.content:
                    break
                try:
                    concepts.append(json.loads(reply.content))
                    logger.debug("Chunk %d processed on attempt %d.", i, attempt + 1)
                    break
                except JSONDecodeError:
                    logger.warning(
                        "Chunk %d: invalid JSON on attempt %d, retrying.", i, attempt + 1
                    )
            else:
                logger.error("Chunk %d: could not parse JSON after 10 attempts.", i)

        all_entities = [
            entity
            for concept in concepts
            for entity in concept.get("Entities", [])
        ]
        docs = [
            Document(
                page_content=f"{list(e.keys())[0]}: {list(e.values())[0]}"
            )
            for e in all_entities
            if e
        ]
        embeddings = OpenAIEmbeddings()
        Qdrant.from_documents(
            docs,
            embeddings,
            path=self.host_object.path,
            collection_name=event.collection_name,
        )
        logger.info(
            "Agent %s created NER collection '%s'.",
            event.sender_id,
            event.collection_name,
        )
        self.host_object.send_event(
            VectorStoreCollectionCreated(
                sender_id=self.host_object.id,
                target_id=event.sender_id,
                collection_name=event.collection_name,
                has_been_created=True,
            )
        )
        self.host_object.is_busy = False


class VectorStoreCollectionRetrieveQuery(AbstractEvent):
    event_type: str = "agent_sends_query_to_retrieve_chunks"
    description: str = "Retrieve chunks from a Qdrant collection by similarity."
    collection_name: str
    query: str
    num_chunks: int = 5
    sender_id: str


class VectorStoreCollectionSimilarChunks(AbstractEvent):
    event_type: str = "vector_store_collection_similar_chunks"
    description: str = "Similar text chunks from a Qdrant collection."
    collection_name: str
    similar_chunks: List[str]
    sender_id: str


class RetrieveChunksBySimilarity(AbstractAction):
    trigger_event_class = VectorStoreCollectionRetrieveQuery
    description = "Retrieve text chunks from a Qdrant collection similar to a query."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: VectorStoreCollectionRetrieveQuery):
        embeddings = OpenAIEmbeddings()
        client = QdrantClient(path=self.host_object.path)
        qdrant = Qdrant(
            client=client,
            collection_name=event.collection_name,
            embeddings=embeddings,
        )
        similar_chunks = [
            el.page_content
            for el in qdrant.similarity_search(event.query, k=event.num_chunks)
        ]
        logger.info(
            "Agent %s retrieved %d chunks from '%s'.",
            event.sender_id,
            len(similar_chunks),
            event.collection_name,
        )
        self.host_object.send_event(
            VectorStoreCollectionSimilarChunks(
                sender_id=self.host_object.id,
                target_id=event.sender_id,
                collection_name=event.collection_name,
                similar_chunks=similar_chunks,
            )
        )


class QdrantBucket(AbstractObject):
    def __init__(self, id: str, path: str = "./vector_store.qdrant"):
        self.path = path
        self.is_busy = False
        actions = [
            GenerateTextChunkCollection(host_object=self),
            GenerateNERCollection(host_object=self),
            RetrieveChunksBySimilarity(host_object=self),
        ]
        super().__init__(
            name="Qdrant Bucket",
            description=(
                "Manages interactions with the Qdrant vector store: generating text "
                "chunk collections, NER collections, and similarity retrieval."
            ),
            id=id,
            actions=actions,
        )
