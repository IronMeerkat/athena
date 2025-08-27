from __future__ import annotations

from typing import Optional

from langchain_community.vectorstores.pgvector import PGVector
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever

from athena_server.config import Settings


def get_vectorstore(
    settings: Settings,
    embeddings: Embeddings,
    *,
    collection_name: Optional[str] = None,
) -> PGVector:
    """Create or access a PGVector-backed vector store collection.

    The underlying tables are managed by langchain's PGVector integration and
    will be created if they don't exist.
    """
    return PGVector(
        embedding_function=embeddings,
        collection_name=collection_name or settings.vector_collection,
        connection_string=settings.postgres_dsn,
        use_jsonb=True,
        distance_strategy=DistanceStrategy.EUCLIDEAN_DISTANCE
    )


def get_retriever(
    vectorstore: PGVector,
    *,
    k: int = 4,
    score_threshold: Optional[float] = None,
    search_type: str = "similarity",
) -> VectorStoreRetriever:
    """Build a retriever from a vector store with sensible defaults."""
    search_kwargs = {"k": k}
    if score_threshold is not None:
        search_kwargs["score_threshold"] = score_threshold
    return vectorstore.as_retriever(
        search_type=search_type,
        search_kwargs=search_kwargs,
    )
