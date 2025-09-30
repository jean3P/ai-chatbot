# apps/adapters/retrieval/fake.py

"""
Fake Vector Store for testing
"""

from typing import Dict, List, Optional
from uuid import UUID

from apps.domain.models import ChunkResult


class FakeVectorStore:
    """
    Fake vector store that returns predetermined results
    """

    def __init__(self, results: Optional[List[ChunkResult]] = None):
        """
        Initialize fake store

        Args:
            results: Predetermined results to return
        """
        self.results = results or []
        self.search_called = False
        self.add_vectors_called = False
        self.last_query = None
        self._vectors = []

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[ChunkResult]:
        """Return predetermined results"""
        self.search_called = True
        self.last_query = query_embedding
        return self.results[:top_k]

    def add_vectors(
        self, chunk_ids: List[UUID], embeddings: List[List[float]], metadata: List[Dict]
    ) -> None:
        """Track that vectors were added"""
        self.add_vectors_called = True
        self._vectors.extend(embeddings)

    def delete_vectors(self, chunk_ids: List[UUID]) -> None:
        """Track deletion"""
        pass

    def count(self) -> int:
        """Return count of stored vectors"""
        return len(self._vectors)
