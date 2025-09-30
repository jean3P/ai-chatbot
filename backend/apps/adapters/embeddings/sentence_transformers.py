# apps/adapters/embeddings/sentence_transformers.py
"""
SentenceTransformers Embedding Adapter

Implements IEmbeddingProvider using local SentenceTransformers models.
"""
import logging
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from apps.domain.models import EmbeddingError

logger = logging.getLogger(__name__)


class SentenceTransformersEmbedding:
    """
    Local embedding provider using SentenceTransformers

    Runs models locally without API calls.
    Free, fast, and no rate limits.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        """
        Initialize SentenceTransformers embeddings

        Args:
            model_name: Model identifier (e.g., "all-MiniLM-L6-v2")
            device: Device to use ("cpu" or "cuda")
        """
        self.model_name = model_name
        self.device = device

        try:
            logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name, device=device)
            self._dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Dimension: {self._dimension}")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise EmbeddingError(f"Model loading failed: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []

        try:
            # Clean and validate inputs
            texts = [str(t).strip() if t else "" for t in texts]
            texts = [t for t in texts if t]  # Remove empty strings

            if not texts:
                return []

            logger.debug(f"Embedding batch of {len(texts)} texts")

            # Generate embeddings
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,  # L2 normalization
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            # Convert to list of lists
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()

            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for single text

        Args:
            text: Text string

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Text cannot be empty")

        try:
            logger.debug(f"Embedding query: {text[:50]}...")

            embedding = self.model.encode(
                text.strip(),
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            # Convert to list
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()

            return embedding

        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise EmbeddingError(f"Query embedding failed: {e}")

    def dimension(self) -> int:
        """
        Get embedding dimension

        Returns:
            Dimension of embedding vectors
        """
        return self._dimension
