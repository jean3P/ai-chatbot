# apps/adapters/retrieval/numpy_db_store.py

"""
NumPy Vector Store with Database Loading

Loads embeddings from Django database into memory for fast similarity search.
Compatible with SQLite.
"""

import logging
from apps.adapters.retrieval.numpy_store import NumPyVectorStore

logger = logging.getLogger(__name__)


class NumPyDBVectorStore(NumPyVectorStore):
    """
    NumPy store that loads embeddings from Django database

    Works with SQLite and any database backend.
    """

    def __init__(self, auto_load: bool = True):
        """
        Initialize store

        Args:
            auto_load: Automatically load embeddings from database
        """
        super().__init__()
        self._loaded = False

        if auto_load:
            self.load_from_database()

    def load_from_database(self) -> int:
        """
        Load all embeddings from Django database

        Returns:
            Number of embeddings loaded
        """
        try:
            # Import here to avoid circular imports
            from apps.documents.models import DocumentChunk

            logger.info("Loading embeddings from database...")

            # Get all chunks with embeddings
            chunks = DocumentChunk.objects.select_related('document').exclude(
                embedding__isnull=True
            )

            chunk_count = chunks.count()
            if chunk_count == 0:
                logger.warning("No chunks with embeddings found in database")
                return 0

            # Prepare data
            chunk_ids = []
            vectors = []
            metadata = []

            for chunk in chunks:
                chunk_ids.append(chunk.id)
                vectors.append(chunk.embedding)
                metadata.append({
                    'document_id': str(chunk.document.id),
                    'document_title': chunk.document.title,
                    'document_type': chunk.document.document_type,
                    'page_number': chunk.page_number,
                    'section_title': chunk.section_title or '',
                    'content': chunk.content,
                    'embedding_model': chunk.metadata.get('embedding_model', 'unknown') if chunk.metadata else 'unknown'
                })

            # Add to store
            self.add_vectors(chunk_ids, vectors, metadata)
            self._loaded = True

            logger.info(f"Loaded {len(vectors)} embeddings from database")
            return len(vectors)

        except Exception as e:
            logger.error(f"Error loading embeddings from database: {e}")
            return 0

    def refresh(self) -> int:
        """
        Refresh embeddings from database

        Returns:
            Number of embeddings loaded
        """
        self.clear()
        return self.load_from_database()
