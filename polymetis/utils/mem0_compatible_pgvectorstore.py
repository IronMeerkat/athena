"""
Mem0-compatible PGVectorStore subclass.

This module provides a subclass of PGVectorStore that includes the add_embeddings method
expected by mem0, while maintaining all original PGVectorStore functionality.
"""

from typing import List, Optional, Any, Dict
from langchain_postgres import PGVectorStore, PGEngine
from langchain_core.embeddings import Embeddings
from langchain_postgres.v2.indexes import DistanceStrategy
from athena_logging import get_logger

logger = get_logger(__name__)


class Mem0CompatiblePGVectorStore(PGVectorStore):
    """
    PGVectorStore subclass with mem0-compatible interface.

    This class extends PGVectorStore to provide the add_embeddings method that mem0 expects,
    while maintaining full compatibility with the parent class.
    """

    def add_embeddings(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        **kwargs
    ) -> List[str]:
        """
        Add embeddings to the vector store.

        This method provides the interface that mem0 expects. The embeddings parameter
        is ignored since PGVectorStore computes embeddings automatically from texts
        using the configured embedding service.

        Args:
            texts: List of texts to add
            embeddings: List of embeddings (ignored - computed automatically)
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of document IDs
            **kwargs: Additional keyword arguments

        Returns:
            List of document IDs
        """
        try:
            logger.debug(f"Adding {len(texts)} texts via add_embeddings method")

            # Use the parent class's add_texts method
            # PGVectorStore will compute embeddings automatically using the embedding service
            result = self.add_texts(
                texts=texts,
                metadatas=metadatas,
                ids=ids,
                **kwargs
            )

            logger.info(f"Successfully added {len(texts)} texts to PGVectorStore")
            return result

        except Exception as e:
            logger.exception(f"Failed to add embeddings to PGVectorStore: {e}")
            raise

    @classmethod
    def create_sync(
        cls,
        engine: PGEngine,
        embedding_service: Embeddings,
        table_name: str = "langchain_pg_embedding",
        schema_name: str = "public",
        distance_strategy: DistanceStrategy = DistanceStrategy.COSINE_DISTANCE,
        **kwargs
    ) -> "Mem0CompatiblePGVectorStore":
        """
        Create a new Mem0CompatiblePGVectorStore instance synchronously.

        This method creates the parent PGVectorStore instance and then changes its class
        to our subclass to add the add_embeddings method.

        Args:
            engine: PGEngine instance
            embedding_service: Embeddings service for computing embeddings
            table_name: Name of the database table
            schema_name: Database schema name
            distance_strategy: Vector distance strategy
            **kwargs: Additional keyword arguments

        Returns:
            Mem0CompatiblePGVectorStore instance
        """
        # Create the parent instance using the parent's create_sync method
        parent_instance = super().create_sync(
            engine=engine,
            embedding_service=embedding_service,
            table_name=table_name,
            schema_name=schema_name,
            distance_strategy=distance_strategy,
            **kwargs
        )

        # Change the instance's class to our subclass
        parent_instance.__class__ = cls

        logger.info(f"Created Mem0CompatiblePGVectorStore with table '{schema_name}.{table_name}'")
        return parent_instance
