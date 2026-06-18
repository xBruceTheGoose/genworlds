import logging

logger = logging.getLogger(__name__)


def run_chroma_to_qdrant_migration(
    collections: list[str], chroma_db_path: str, qdrant_db_path: str
):
    """Migrate vector collections from ChromaDB to Qdrant."""
    import os
    import chromadb
    from dotenv import load_dotenv
    from langchain_community.vectorstores import Chroma, Qdrant
    from langchain_openai import OpenAIEmbeddings
    from qdrant_client.http import models as rest
    from qdrant_client import QdrantClient

    load_dotenv(dotenv_path=".env")

    embeddings_model = OpenAIEmbeddings()
    qdrant_client = QdrantClient(path=qdrant_db_path)

    for collection_name in collections:
        logger.info("Migrating collection '%s'", collection_name)
        client_settings = chromadb.config.Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=chroma_db_path,
            anonymized_telemetry=False,
        )

        collection = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings_model,
            client_settings=client_settings,
            persist_directory=chroma_db_path,
        )

        items = collection._collection.get(
            include=["embeddings", "metadatas", "documents"]
        )

        # Use create_collection with recreate logic instead of the removed recreate_collection
        existing = {
            c.name for c in qdrant_client.get_collections().collections
        }
        if collection_name in existing:
            qdrant_client.delete_collection(collection_name)
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=rest.VectorParams(
                distance=rest.Distance.COSINE,
                size=1536,
            ),
        )

        CONTENT_KEY = "page_content"
        METADATA_KEY = "metadata"

        qdrant_client.upsert(
            collection_name=collection_name,
            points=rest.Batch.construct(
                ids=items["ids"],
                vectors=items["embeddings"],
                payloads=Qdrant._build_payloads(
                    items["documents"], items["metadatas"], CONTENT_KEY, METADATA_KEY
                ),
            ),
        )

    logger.info("Migration complete.")
