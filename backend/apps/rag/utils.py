# /backend/apps/rag/utils.py

"""
RAG utility functions for document processing and vector operations
"""
import json
import logging
from typing import Any, Dict, List, Tuple

import numpy as np
from django.utils import timezone
from sklearn.metrics.pairwise import cosine_similarity

from apps.documents.models import Document, DocumentChunk

logger = logging.getLogger(__name__)


class VectorStore:
    """In-memory vector store for similarity search"""

    def __init__(self):
        self.vectors = []
        self.chunk_ids = []
        self.metadata = []
        self.dimension = None

    def add_vectors(
        self,
        chunk_ids: List[str],
        vectors: List[List[float]],
        metadata: List[Dict] = None,
    ):
        """Add vectors to the store"""
        if not vectors:
            return

        # Set dimension from first vector
        if self.dimension is None:
            self.dimension = len(vectors[0])

        # Validate all vectors have same dimension
        for vector in vectors:
            if len(vector) != self.dimension:
                raise ValueError(
                    f"Vector dimension mismatch: expected {self.dimension}, got {len(vector)}"
                )

        self.vectors.extend(vectors)
        self.chunk_ids.extend(chunk_ids)
        self.metadata.extend(metadata or [{}] * len(vectors))

    def search(
        self, query_vector: List[float], top_k: int = 10, min_score: float = 0.0
    ) -> List[Dict]:
        """Search for similar vectors"""
        if not self.vectors or len(query_vector) != self.dimension:
            return []

        # Calculate similarities
        query_array = np.array([query_vector])
        vectors_array = np.array(self.vectors)

        similarities = cosine_similarity(query_array, vectors_array)[0]

        # Create results with scores
        results = []
        for i, score in enumerate(similarities):
            if score >= min_score:
                results.append(
                    {
                        "chunk_id": self.chunk_ids[i],
                        "score": float(score),
                        "metadata": self.metadata[i],
                    }
                )

        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def size(self) -> int:
        """Get number of vectors in store"""
        return len(self.vectors)

    def clear(self):
        """Clear all vectors"""
        self.vectors.clear()
        self.chunk_ids.clear()
        self.metadata.clear()
        self.dimension = None


def load_embeddings_to_memory() -> VectorStore:
    """Load all embeddings from database to memory for fast searching"""
    store = VectorStore()

    try:
        # Get all chunks with embeddings
        chunks = DocumentChunk.objects.select_related("document").exclude(
            embedding__isnull=True
        )

        chunk_ids = []
        vectors = []
        metadata = []

        for chunk in chunks:
            chunk_ids.append(str(chunk.id))
            vectors.append(chunk.embedding)
            metadata.append(
                {
                    "document_id": str(chunk.document.id),
                    "document_title": chunk.document.title,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "content_preview": chunk.content[:200],
                }
            )

        if vectors:
            store.add_vectors(chunk_ids, vectors, metadata)
            logger.info(f"Loaded {len(vectors)} embeddings to memory")

        return store

    except Exception as e:
        logger.error(f"Error loading embeddings to memory: {e}")
        return store


def calculate_chunk_similarity(
    chunk1_embedding: List[float], chunk2_embedding: List[float]
) -> float:
    """Calculate cosine similarity between two chunk embeddings"""
    try:
        if not chunk1_embedding or not chunk2_embedding:
            return 0.0

        # Convert to numpy arrays
        vec1 = np.array([chunk1_embedding])
        vec2 = np.array([chunk2_embedding])

        # Calculate cosine similarity
        similarity = cosine_similarity(vec1, vec2)[0][0]
        return float(similarity)

    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return 0.0


def find_duplicate_chunks(
    similarity_threshold: float = 0.95,
) -> List[Tuple[str, str, float]]:
    """Find potentially duplicate chunks based on embedding similarity"""
    duplicates = []

    try:
        chunks = list(
            DocumentChunk.objects.exclude(embedding__isnull=True).values(
                "id", "embedding"
            )
        )

        for i, chunk1 in enumerate(chunks):
            for chunk2 in chunks[i + 1 :]:
                similarity = calculate_chunk_similarity(
                    chunk1["embedding"], chunk2["embedding"]
                )

                if similarity >= similarity_threshold:
                    duplicates.append(
                        (str(chunk1["id"]), str(chunk2["id"]), similarity)
                    )

        logger.info(f"Found {len(duplicates)} potential duplicate chunk pairs")
        return duplicates

    except Exception as e:
        logger.error(f"Error finding duplicate chunks: {e}")
        return []


def optimize_chunk_embeddings():
    """Optimize embeddings storage - remove duplicates, update outdated embeddings"""
    try:
        # Find and log duplicates
        duplicates = find_duplicate_chunks()

        if duplicates:
            logger.warning(f"Found {len(duplicates)} potential duplicate chunks")
            for chunk1_id, chunk2_id, similarity in duplicates[:10]:  # Log first 10
                logger.warning(
                    f"Chunks {chunk1_id} and {chunk2_id} have similarity {similarity:.3f}"
                )

        # Find chunks without embeddings
        chunks_without_embeddings = DocumentChunk.objects.filter(
            embedding__isnull=True
        ).count()
        if chunks_without_embeddings > 0:
            logger.info(f"Found {chunks_without_embeddings} chunks without embeddings")

        # Find documents that need reprocessing
        unprocessed_docs = Document.objects.filter(processed=False).count()
        if unprocessed_docs > 0:
            logger.info(f"Found {unprocessed_docs} unprocessed documents")

        return {
            "duplicates": len(duplicates),
            "chunks_without_embeddings": chunks_without_embeddings,
            "unprocessed_documents": unprocessed_docs,
        }

    except Exception as e:
        logger.error(f"Error optimizing embeddings: {e}")
        return {}


def export_embeddings_to_json(output_file: str) -> bool:
    """Export all embeddings to JSON file for backup"""
    try:
        chunks = DocumentChunk.objects.select_related("document").exclude(
            embedding__isnull=True
        )

        export_data = {
            "version": "1.0",
            "export_timestamp": str(timezone.now()),
            "chunks": [],
        }

        for chunk in chunks:
            chunk_data = {
                "id": str(chunk.id),
                "document_id": str(chunk.document.id),
                "document_title": chunk.document.title,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "content": chunk.content,
                "embedding": chunk.embedding,
                "metadata": chunk.metadata,
            }
            export_data["chunks"].append(chunk_data)

        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(export_data['chunks'])} chunks to {output_file}")
        return True

    except Exception as e:
        logger.error(f"Error exporting embeddings: {e}")
        return False


def import_embeddings_from_json(input_file: str) -> bool:
    """Import embeddings from JSON backup file"""
    try:
        with open(input_file, "r") as f:
            import_data = json.load(f)

        chunks_data = import_data.get("chunks", [])
        imported_count = 0

        for chunk_data in chunks_data:
            try:
                chunk_id = chunk_data["id"]
                chunk = DocumentChunk.objects.get(id=chunk_id)

                # Update embedding if it's missing
                if not chunk.embedding:
                    chunk.embedding = chunk_data["embedding"]
                    chunk.save(update_fields=["embedding"])
                    imported_count += 1

            except DocumentChunk.DoesNotExist:
                logger.warning(f"Chunk {chunk_id} not found in database")
                continue

        logger.info(f"Imported embeddings for {imported_count} chunks")
        return True

    except Exception as e:
        logger.error(f"Error importing embeddings: {e}")
        return False


def validate_embeddings() -> Dict[str, Any]:
    """Validate embedding integrity and consistency"""
    results = {
        "total_chunks": 0,
        "chunks_with_embeddings": 0,
        "chunks_without_embeddings": 0,
        "invalid_embeddings": 0,
        "dimension_consistency": True,
        "dimensions_found": set(),
    }

    try:
        chunks = DocumentChunk.objects.all()
        results["total_chunks"] = chunks.count()

        for chunk in chunks:
            if chunk.embedding:
                results["chunks_with_embeddings"] += 1

                # Check if embedding is valid
                if not isinstance(chunk.embedding, list) or not chunk.embedding:
                    results["invalid_embeddings"] += 1
                    continue

                # Check dimensions
                dimension = len(chunk.embedding)
                results["dimensions_found"].add(dimension)

                # Validate embedding values
                try:
                    np.array(chunk.embedding, dtype=float)
                except (ValueError, TypeError):
                    results["invalid_embeddings"] += 1

            else:
                results["chunks_without_embeddings"] += 1

        # Check dimension consistency
        if len(results["dimensions_found"]) > 1:
            results["dimension_consistency"] = False
            logger.warning(
                f"Inconsistent embedding dimensions found: {results['dimensions_found']}"
            )

        results["dimensions_found"] = list(results["dimensions_found"])

        logger.info(f"Embedding validation complete: {results}")
        return results

    except Exception as e:
        logger.error(f"Error validating embeddings: {e}")
        return results


# Global vector store instance (loaded on demand)
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get global vector store instance, loading embeddings if needed"""
    global _vector_store

    if _vector_store is None or _vector_store.size() == 0:
        _vector_store = load_embeddings_to_memory()

    return _vector_store


def refresh_vector_store():
    """Refresh the global vector store with latest embeddings"""
    global _vector_store
    _vector_store = load_embeddings_to_memory()
