# apps/domain/ports/retriever.py

"""
Vector Store Port - Interface for similarity search

This port defines the contract for vector similarity search.
"""

from typing import Dict, List, Optional, Protocol
from uuid import UUID

from apps.domain.models import ChunkResult


class IVectorStore(Protocol):
    """
    Interface for vector similarity search

    Implementations must support adding vectors and searching by similarity.
    """

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[ChunkResult]:
        """
        Find most similar vectors to query

        Args:
            query_embedding: Query vector to search for
            top_k: Maximum number of results to return
            filters: Optional metadata filters
                Example: {'document_type': 'manual', 'language': 'en'}

        Returns:
            List of ChunkResult objects sorted by similarity (highest first)

        Raises:
            RetrieverError: If search fails
            EmbeddingDimensionMismatchError: If query dimension doesn't match store

        Example:
            results = store.search([0.1, 0.2, ...], top_k=5)
            results[0].score  # Highest similarity score
            0.95
        """
        ...

    def add_vectors(
        self, chunk_ids: List[UUID], embeddings: List[List[float]], metadata: List[Dict]
    ) -> None:
        """
        Add vectors to the store

        Args:
            chunk_ids: List of chunk UUIDs
            embeddings: List of embedding vectors (must match chunk_ids length)
            metadata: List of metadata dicts (must match chunk_ids length)

        Raises:
            RetrieverError: If adding vectors fails
            EmbeddingDimensionMismatchError: If dimensions don't match

        Note:
            All embeddings must have the same dimension.
            Metadata can include: content, document_title, page_number, etc.
        """
        ...

    def delete_vectors(self, chunk_ids: List[UUID]) -> None:
        """
        Remove vectors from the store

        Args:
            chunk_ids: List of chunk UUIDs to remove

        Raises:
            RetrieverError: If deletion fails
        """
        ...

    def count(self) -> int:
        """
        Get total number of vectors in store

        Returns:
            Integer count of stored vectors
        """
        ...
