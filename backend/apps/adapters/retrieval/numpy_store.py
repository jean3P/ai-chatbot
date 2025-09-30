# apps/adapters/retrieval/numpy_store.py
"""
NumPy Vector Store - In-memory similarity search

Fast in-memory vector store for development and testing.
"""
from typing import Dict, List, Optional
from uuid import UUID

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from apps.domain.models import ChunkResult, EmbeddingDimensionMismatchError


class NumPyVectorStore:
    """
    In-memory vector store using NumPy

    Uses brute-force cosine similarity for search.
    Suitable for development and small datasets (<100K vectors).
    """

    def __init__(self):
        """Initialize empty vector store"""
        self.vectors: List[List[float]] = []
        self.chunk_ids: List[UUID] = []
        self.metadata: List[Dict] = []
        self._dimension: Optional[int] = None

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[ChunkResult]:
        """
        Find similar vectors using cosine similarity

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filters: Not implemented in NumPy store

        Returns:
            List of ChunkResult objects sorted by similarity
        """
        if not self.vectors:
            return []

        # Validate dimension
        if self._dimension and len(query_embedding) != self._dimension:
            raise EmbeddingDimensionMismatchError(
                f"Query dimension {len(query_embedding)} doesn't match "
                f"store dimension {self._dimension}"
            )

        # Calculate similarities
        query = np.array([query_embedding])
        vectors = np.array(self.vectors)
        similarities = cosine_similarity(query, vectors)[0]

        # Get top k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Build results
        results = []
        for idx in top_indices:
            results.append(
                ChunkResult(
                    chunk_id=self.chunk_ids[idx],
                    content=self.metadata[idx].get("content", ""),
                    score=float(similarities[idx]),
                    metadata=self.metadata[idx],
                )
            )

        return results

    def add_vectors(
        self, chunk_ids: List[UUID], embeddings: List[List[float]], metadata: List[Dict]
    ) -> None:
        """
        Add vectors to the store

        Args:
            chunk_ids: List of UUIDs
            embeddings: List of vectors
            metadata: List of metadata dicts
        """
        if len(chunk_ids) != len(embeddings) != len(metadata):
            raise ValueError(
                "chunk_ids, embeddings, and metadata must have same length"
            )

        if not embeddings:
            return

        # Set or validate dimension
        dim = len(embeddings[0])
        if self._dimension is None:
            self._dimension = dim
        elif self._dimension != dim:
            raise EmbeddingDimensionMismatchError(
                f"Embedding dimension {dim} doesn't match store dimension {self._dimension}"
            )

        # Validate all embeddings have same dimension
        for emb in embeddings:
            if len(emb) != self._dimension:
                raise EmbeddingDimensionMismatchError(
                    f"All embeddings must have dimension {self._dimension}"
                )

        # Add to store
        self.chunk_ids.extend(chunk_ids)
        self.vectors.extend(embeddings)
        self.metadata.extend(metadata)

    def delete_vectors(self, chunk_ids: List[UUID]) -> None:
        """
        Remove vectors from store

        Args:
            chunk_ids: List of UUIDs to remove
        """
        ids_to_remove = set(chunk_ids)

        # Filter out removed items
        new_ids = []
        new_vectors = []
        new_metadata = []

        for chunk_id, vector, meta in zip(self.chunk_ids, self.vectors, self.metadata):
            if chunk_id not in ids_to_remove:
                new_ids.append(chunk_id)
                new_vectors.append(vector)
                new_metadata.append(meta)

        self.chunk_ids = new_ids
        self.vectors = new_vectors
        self.metadata = new_metadata

    def count(self) -> int:
        """
        Get number of vectors in store

        Returns:
            Count of stored vectors
        """
        return len(self.vectors)

    def clear(self) -> None:
        """Clear all vectors from store"""
        self.vectors.clear()
        self.chunk_ids.clear()
        self.metadata.clear()
        self._dimension = None
