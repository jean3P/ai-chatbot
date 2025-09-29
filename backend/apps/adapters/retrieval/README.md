# Vector Store Adapters

## Purpose
Vector store adapters implement the `IVectorStore` port for similarity search over embeddings.

## Interface

```python
class IVectorStore(Protocol):
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[ChunkResult]:
        """Find similar vectors"""
        ...
    
    def add_vectors(
        self,
        chunk_ids: List[UUID],
        embeddings: List[List[float]],
        metadata: List[Dict]
    ) -> None:
        """Add vectors to store"""
        ...
    
    def delete_vectors(self, chunk_ids: List[UUID]) -> None:
        """Remove vectors from store"""
        ...
```

## Implementations

### 1. NumPyVectorStore
- **Storage**: In-memory (Python lists)
- **Index**: None (brute force)
- **Speed**: ~100ms for 10K vectors
- **Scalability**: Up to 100K vectors
- **Use case**: Development, testing

**Configuration:**
```python
store = NumPyVectorStore()
```

**Pros:**
- Fast iteration (no database needed)
- Simple implementation
- Perfect for testing
- No dependencies

**Cons:**
- Not persistent (lost on restart)
- Slow for large datasets
- No filtering support
- Memory intensive

### 2. PgVectorStore (Production)
- **Storage**: PostgreSQL with pgvector extension
- **Index**: HNSW (Hierarchical Navigable Small World)
- **Speed**: ~50ms for 10M vectors
- **Scalability**: Up to 10M+ vectors
- **Use case**: Production

**Configuration:**
```python
store = PgVectorStore(dimension=384)
```

**Pros:**
- Fast similarity search (HNSW index)
- Persistent storage
- Advanced filtering (SQL WHERE)
- Transactional integrity
- Scales horizontally

**Cons:**
- Requires PostgreSQL setup
- Index building takes time
- More complex than in-memory

### 3. FakeVectorStore
- **Storage**: In-memory (deterministic)
- **Speed**: Instant
- **Use case**: Unit testing

**Configuration:**
```python
store = FakeVectorStore(results=[
    ChunkResult(chunk_id=uuid4(), content="...", score=0.9)
])
```

## NumPy Implementation Example

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class NumPyVectorStore:
    def __init__(self):
        self.vectors = []
        self.chunk_ids = []
        self.metadata = []
    
    def search(self, query_embedding, top_k=10, filters=None):
        if not self.vectors:
            return []
        
        # Calculate similarities
        query = np.array([query_embedding])
        vectors = np.array(self.vectors)
        scores = cosine_similarity(query, vectors)[0]
        
        # Get top k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        # Build results
        results = []
        for idx in top_indices:
            results.append(ChunkResult(
                chunk_id=self.chunk_ids[idx],
                content=self.metadata[idx].get('content', ''),
                score=float(scores[idx]),
                metadata=self.metadata[idx]
            ))
        
        return results
    
    def add_vectors(self, chunk_ids, embeddings, metadata):
        self.chunk_ids.extend(chunk_ids)
        self.vectors.extend(embeddings)
        self.metadata.extend(metadata)
```

## PgVector Implementation Example

```python
from django.db import connection

class PgVectorStore:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
    
    def search(self, query_embedding, top_k=10, filters=None):
        # Use pgvector's <-> operator for cosine distance
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    content,
                    1 - (embedding <-> %s::vector) as score,
                    metadata
                FROM document_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <-> %s::vector
                LIMIT %s
            """, [query_embedding, query_embedding, top_k])
            
            results = []
            for row in cursor.fetchall():
                results.append(ChunkResult(
                    chunk_id=row[0],
                    content=row[1],
                    score=row[2],
                    metadata=row[3]
                ))
            
            return results
    
    def add_vectors(self, chunk_ids, embeddings, metadata):
        # Bulk insert using Django ORM
        from apps.documents.models import DocumentChunk
        
        chunks = []
        for chunk_id, embedding, meta in zip(chunk_ids, embeddings, metadata):
            chunk = DocumentChunk.objects.get(id=chunk_id)
            chunk.embedding = embedding
            chunk.metadata.update(meta)
            chunks.append(chunk)
        
        DocumentChunk.objects.bulk_update(
            chunks,
            ['embedding', 'metadata'],
            batch_size=100
        )
```

## Filtering Support

```python
# Filter by document type
results = store.search(
    query_embedding=embedding,
    top_k=10,
    filters={
        'document_type': 'manual',
        'language': 'en'
    }
)

# PgVector with filters
cursor.execute("""
    SELECT ...
    FROM document_chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE 
        embedding IS NOT NULL
        AND d.document_type = %s
        AND d.language = %s
    ORDER BY embedding <-> %s::vector
    LIMIT %s
""", ['manual', 'en', query_embedding, top_k])
```

## Testing

```python
def test_numpy_vector_store_search():
    """Test in-memory vector store"""
    store = NumPyVectorStore()
    
    # Add vectors
    store.add_vectors(
        chunk_ids=[uuid4(), uuid4()],
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        metadata=[{'content': 'A'}, {'content': 'B'}]
    )
    
    # Search
    results = store.search(
        query_embedding=[0.1, 0.2],
        top_k=2
    )
    
    assert len(results) == 2
    assert results[0].score > results[1].score

@pytest.mark.django_db
def test_pgvector_store_search():
    """Integration test with real database"""
    store = PgVectorStore(dimension=384)
    
    # Create test data
    doc = Document.objects.create(title="Test")
    chunk = DocumentChunk.objects.create(
        document=doc,
        content="Test content",
        embedding=[0.1] * 384
    )
    
    # Search
    results = store.search(
        query_embedding=[0.1] * 384,
        top_k=10
    )
    
    assert len(results) > 0
    assert results[0].chunk_id == chunk.id
```

## Migration Strategy

**Phase 1**: Use NumPy (current)
- Fast development iteration
- No database setup needed
- Test domain logic

**Phase 2**: Add PgVector
- Deploy schema changes
- Backfill embeddings
- Feature flag for cutover
- Keep NumPy as fallback

**Phase 3**: Remove NumPy
- After 2 weeks of stable PgVector
- Delete old code
- Update documentation