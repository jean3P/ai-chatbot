# apps/domain/ports/embeddings.py

"""
Embedding Provider Port - Interface for vector embeddings

This port defines the contract for converting text to vector embeddings.
"""

from typing import List, Protocol


class IEmbeddingProvider(Protocol):
    """
    Interface for embedding providers

    Implementations must convert text to fixed-dimension vectors.
    """

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (one per input text)
            Each vector is a list of floats

        Raises:
            EmbeddingError: If embedding generation fails

        Example:
            embedder.embed_batch(["hello", "world"])
            [[0.1, 0.2, ...], [0.3, 0.4, ...]]
        """
        ...

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingError: If embedding generation fails
        """
        ...

    def dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this provider

        Returns:
            Integer dimension (e.g., 384, 1536)

        Note:
            Must be consistent across all embeddings from this provider.
            Critical for vector store compatibility.
        """
        ...
