# Embedding Adapters

## Purpose
Embedding adapters implement the `IEmbeddingProvider` port for converting text to vectors.

## Interface

```python
class IEmbeddingProvider(Protocol):
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts efficiently"""
        ...
    
    def embed_query(self, text: str) -> List[float]:
        """Embed single query"""
        ...
    
    def dimension(self) -> int:
        """Get embedding dimension"""
        ...
```

## Implementations

### 1. SentenceTransformersEmbedding
- **Model**: all-MiniLM-L6-v2
- **Dimension**: 384
- **Cost**: $0 (local)
- **Speed**: 50ms per batch (50 texts)
- **Quality**: 85% recall@10
- **Use case**: Production MVP

**Configuration:**
```python
embedding = SentenceTransformersEmbedding(
    model_name="all-MiniLM-L6-v2",
    device="cpu"  # or "cuda"
)
```

**Features:**
- No API calls (runs locally)
- No rate limits
- Consistent performance
- GPU acceleration available

### 2. OpenRouterEmbedding (Planned)
- **Model**: text-embedding-3-small
- **Dimension**: 1536
- **Cost**: ~$100/month
- **Speed**: 200ms per batch
- **Quality**: 91% recall@10
- **Use case**: Quality upgrade

### 3. OpenAIEmbedding (Planned)
- **Model**: text-embedding-3-small or text-embedding-3-large
- **Dimension**: 1536 or 3072
- **Cost**: $0.02/1M tokens
- **Speed**: 150ms per batch
- **Use case**: High quality needs

### 4. FakeEmbedding
- **Dimension**: Configurable
- **Cost**: $0
- **Speed**: Instant
- **Use case**: Testing

**Configuration:**
```python
embedding = FakeEmbedding(dimension=384)
```

## Batching Strategy

Process in batches for efficiency:

```python
# Optimal batch size depends on model and hardware
batch_size = 50

for i in range(0, len(texts), batch_size):
    batch = texts[i:i+batch_size]
    embeddings = provider.embed_batch(batch)
    # Process embeddings...
```

## Critical: Dimension Consistency

**Always validate dimensions match:**

```python
# At initialization
expected_dim = 384
actual_dim = embedding_provider.dimension()

if actual_dim != expected_dim:
    raise EmbeddingDimensionMismatchError(
        f"Expected {expected_dim}, got {actual_dim}"
    )

# Before storing
for emb in embeddings:
    if len(emb) != expected_dim:
        raise ValueError(f"Invalid embedding dimension: {len(emb)}")
```

## Caching Strategy

Cache embeddings for queries to reduce API calls:

```python
class CachedEmbeddingProvider:
    def __init__(self, provider: IEmbeddingProvider):
        self._provider = provider
        self._cache = {}
    
    def embed_query(self, text: str) -> List[float]:
        cache_key = hashlib.md5(text.encode()).hexdigest()
        
        if cache_key not in self._cache:
            self._cache[cache_key] = self._provider.embed_query(text)
        
        return self._cache[cache_key]
```

## Error Handling

```python
class SentenceTransformersEmbedding:
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            # Clean inputs
            texts = [str(t).strip() for t in texts if t]
            
            if not texts:
                return []
            
            # Generate embeddings
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise EmbeddingError(f"Failed to generate embeddings: {e}")
```

## Testing

```python
def test_sentence_transformers_embedding():
    """Test local embedding generation"""
    provider = SentenceTransformersEmbedding(
        model_name="all-MiniLM-L6-v2"
    )
    
    texts = ["Hello world", "Test document"]
    embeddings = provider.embed_batch(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384

def test_fake_embedding():
    """Test fake embedding for unit tests"""
    provider = FakeEmbedding(dimension=384)
    
    embedding = provider.embed_query("test")
    
    assert len(embedding) == 384
    assert all(isinstance(x, float) for x in embedding)
```

## Migration Notes

Current embedding code in `apps/core/openrouter.py` will be refactored:
- Extract SentenceTransformers usage
- Add proper error handling
- Implement IEmbeddingProvider interface
- Add dimension validation
- Remove fallback logic (handle in service layer)