# apps/adapters/embeddings/fake.py
"""
Fake Embedding Provider for testing

Generates deterministic embeddings without computation.
"""
from typing import List
import hashlib


class FakeEmbedding:
    """
    Fake embedding implementation for unit testing

    Generates deterministic vectors based on text hash.
    """

    def __init__(self, dimension: int = 384):
        """
        Initialize fake embeddings

        Args:
            dimension: Vector dimension to generate
        """
        self._dimension = dimension
        self.embed_batch_called = False
        self.embed_query_called = False

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate fake embeddings for texts

        Args:
            texts: List of text strings

        Returns:
            List of fake embedding vectors

        Note:
            Same text always produces same embedding (deterministic)
        """
        self.embed_batch_called = True
        return [self._generate_embedding(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        """
        Generate fake embedding for single text

        Args:
            text: Text string

        Returns:
            Fake embedding vector
        """
        self.embed_query_called = True
        return self._generate_embedding(text)

    def dimension(self) -> int:
        """
        Get embedding dimension

        Returns:
            Configured dimension
        """
        return self._dimension

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate deterministic embedding from text

        Uses hash of text to generate consistent vectors.
        """
        # Use hash for deterministic but varied values
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)

        # Generate dimension number of floats
        embedding = []
        for i in range(self._dimension):
            # Generate value between -1 and 1
            val = ((hash_val + i) % 1000) / 500.0 - 1.0
            embedding.append(val)

        return embedding
