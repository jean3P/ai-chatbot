# apps/adapters/retrieval/pgvector_store.py
"""
PgVector Store Adapter

Implements IVectorStore using PostgreSQL with pgvector extension.
"""
from typing import List, Dict, Optional
from uuid import UUID
import logging
from django.db import connection

from apps.domain.models import ChunkResult, EmbeddingDimensionMismatchError, RetrieverError

logger = logging.getLogger(__name__)


class PgVectorStore:
    """
    PostgreSQL + pgvector implementation of vector store

    Uses HNSW index for fast similarity search.
    Suitable for production with millions of vectors.
    """

    def __init__(self, dimension: int = 384):
        """
        Initialize pgvector store

        Args:
            dimension: Expected embedding dimension
        """
        self._dimension = dimension
        self._validate_extension()

    def _validate_extension(self):
        """Verify pgvector extension is available"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                result = cursor.fetchone()

                if not result:
                    logger.warning("pgvector extension not installed")
                else:
                    logger.info(f"pgvector extension version: {result[0]}")

        except Exception as e:
            logger.warning(f"Could not verify pgvector extension: {e}")

    def search(
            self,
            query_embedding: List[float],
            top_k: int = 10,
            filters: Optional[Dict] = None
    ) -> List[ChunkResult]:
        """
        Search for similar vectors using pgvector

        Args:
            query_embedding: Query vector
            top_k: Number of results
            filters: Optional metadata filters

        Returns:
            List of ChunkResult objects

        Raises:
            RetrieverError: If search fails
        """
        # Validate dimension
        if len(query_embedding) != self._dimension:
            raise EmbeddingDimensionMismatchError(
                f"Query dimension {len(query_embedding)} doesn't match "
                f"expected dimension {self._dimension}"
            )

        try:
            with connection.cursor() as cursor:
                # Build query
                base_query = """
                    SELECT 
                        c.id,
                        c.content,
                        1 - (c.embedding <=> %s::vector) as similarity,
                        c.metadata,
                        d.title as document_title,
                        d.document_type,
                        c.page_number,
                        c.section_title
                    FROM document_chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE c.embedding IS NOT NULL
                """

                params = [query_embedding]

                # Add filters if provided
                if filters:
                    if 'document_type' in filters:
                        base_query += " AND d.document_type = %s"
                        params.append(filters['document_type'])

                    if 'language' in filters:
                        base_query += " AND d.language = %s"
                        params.append(filters['language'])

                # Order by similarity and limit
                base_query += """
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                """
                params.extend([query_embedding, top_k])

                logger.debug(f"Executing pgvector search with top_k={top_k}")
                cursor.execute(base_query, params)

                # Build results
                results = []
                for row in cursor.fetchall():
                    results.append(ChunkResult(
                        chunk_id=row[0],
                        content=row[1],
                        score=float(row[2]),
                        metadata={
                            'document_title': row[4],
                            'document_type': row[5],
                            'page_number': row[6],
                            'section_title': row[7],
                            **row[3]  # Include existing metadata
                        }
                    ))

                logger.info(f"Found {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Error in pgvector search: {e}")
            raise RetrieverError(f"Search failed: {e}")

    def add_vectors(
            self,
            chunk_ids: List[UUID],
            embeddings: List[List[float]],
            metadata: List[Dict]
    ) -> None:
        """
        Add vectors to pgvector store

        Args:
            chunk_ids: List of chunk UUIDs
            embeddings: List of vectors
            metadata: List of metadata dicts

        Raises:
            RetrieverError: If adding fails
        """
        if len(chunk_ids) != len(embeddings) != len(metadata):
            raise ValueError("chunk_ids, embeddings, and metadata must have same length")

        if not embeddings:
            return

        # Validate dimensions
        for emb in embeddings:
            if len(emb) != self._dimension:
                raise EmbeddingDimensionMismatchError(
                    f"Embedding dimension {len(emb)} doesn't match {self._dimension}"
                )

        try:
            from apps.documents.models import DocumentChunk

            # Bulk update using Django ORM
            chunks_to_update = []
            for chunk_id, embedding, meta in zip(chunk_ids, embeddings, metadata):
                try:
                    chunk = DocumentChunk.objects.get(id=chunk_id)
                    chunk.embedding = embedding

                    # Merge metadata
                    if not chunk.metadata:
                        chunk.metadata = {}
                    chunk.metadata.update(meta)

                    chunks_to_update.append(chunk)

                except DocumentChunk.DoesNotExist:
                    logger.warning(f"Chunk {chunk_id} not found")
                    continue

            if chunks_to_update:
                DocumentChunk.objects.bulk_update(
                    chunks_to_update,
                    ['embedding', 'metadata'],
                    batch_size=100
                )
                logger.info(f"Updated {len(chunks_to_update)} chunks with embeddings")

        except Exception as e:
            logger.error(f"Error adding vectors: {e}")
            raise RetrieverError(f"Failed to add vectors: {e}")

    def delete_vectors(self, chunk_ids: List[UUID]) -> None:
        """
        Delete vectors from store

        Args:
            chunk_ids: List of chunk UUIDs to delete
        """
        try:
            from apps.documents.models import DocumentChunk

            # Clear embeddings
            DocumentChunk.objects.filter(id__in=chunk_ids).update(embedding=None)
            logger.info(f"Cleared embeddings for {len(chunk_ids)} chunks")

        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
            raise RetrieverError(f"Failed to delete vectors: {e}")

    def count(self) -> int:
        """
        Get count of vectors in store

        Returns:
            Number of vectors
        """
        try:
            from apps.documents.models import DocumentChunk
            return DocumentChunk.objects.exclude(embedding__isnull=True).count()

        except Exception as e:
            logger.error(f"Error counting vectors: {e}")
            return 0
