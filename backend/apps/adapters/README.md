# Adapters (Infrastructure Layer)

## Overview
Adapters are **concrete implementations** of port interfaces. They handle all communication with external systems (databases, APIs, filesystems, etc.).

## Dependency Rule
```
Domain (defines ports) ← Adapters (implement ports)
```
Adapters depend on domain interfaces, not vice versa.

## Structure

```
adapters/
├── llm/              # LLM provider implementations
├── embeddings/       # Embedding provider implementations
├── retrieval/        # Vector store implementations
├── parsing/          # Document parser implementations
└── repositories/     # Data persistence implementations
```

## Adapter Categories

### 1. LLM Adapters (`llm/`)
Implement `ILLMProvider` port for text generation.

**Implementations:**
- `OpenRouterLLM` - OpenRouter API wrapper
- `AnthropicLLM` - Direct Anthropic Claude API
- `OpenAILLM` - OpenAI GPT API
- `FakeLLM` - Testing/development

### 2. Embedding Adapters (`embeddings/`)
Implement `IEmbeddingProvider` port for vector embeddings.

**Implementations:**
- `SentenceTransformersEmbedding` - Local models (free)
- `OpenRouterEmbedding` - OpenRouter embedding API
- `OpenAIEmbedding` - OpenAI embedding API
- `FakeEmbedding` - Testing

### 3. Retrieval Adapters (`retrieval/`)
Implement `IVectorStore` port for similarity search.

**Implementations:**
- `NumPyVectorStore` - In-memory for dev/test
- `PgVectorStore` - PostgreSQL pgvector for production
- `FakeVectorStore` - Testing

### 4. Parsing Adapters (`parsing/`)
Implement `IDocumentParser` port for text extraction.

**Implementations:**
- `PyMuPDFParser` - Primary PDF parser
- `PDFPlumberParser` - Backup PDF parser
- `FakeParser` - Testing

### 5. Repository Adapters (`repositories/`)
Implement repository ports for data persistence.

**Implementations:**
- `DjangoMessageRepository` - ORM-based
- `DjangoConversationRepository` - ORM-based
- `InMemoryRepository` - Testing

## Example: OpenRouter Adapter

```python
# apps/adapters/llm/openrouter.py
from typing import List, Dict, Iterator
import openai
from apps.domain.ports.llm import ILLMProvider

class OpenRouterLLM:
    """OpenRouter API adapter implementing ILLMProvider"""
    
    def __init__(self, api_key: str, model: str, base_url: str):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
    
    def generate(self, messages: List[Dict]) -> str:
        """Implements ILLMProvider.generate"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=1000
        )
        return response.choices[0].message.content
    
    def stream(self, messages: List[Dict]) -> Iterator[str]:
        """Implements ILLMProvider.stream"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

## Configuration

Adapters are configured in `infrastructure/config.py`:

```python
# Test environment
RAG_CONFIG = {
    'llm': {'type': 'fake'},
    'embedding': {'type': 'fake'},
    'retriever': {'type': 'numpy'}
}

# Production environment
RAG_CONFIG = {
    'llm': {
        'type': 'openrouter',
        'api_key': os.getenv('OPENROUTER_API_KEY'),
        'model': 'gpt-4o-mini'
    },
    'embedding': {
        'type': 'sentence_transformers',
        'model': 'all-MiniLM-L6-v2'
    },
    'retriever': {
        'type': 'pgvector',
        'dimension': 384
    }
}
```

## Testing Adapters

Adapters have **integration tests** (use real infrastructure):

```python
@pytest.mark.integration
@pytest.mark.django_db
def test_pgvector_store_search():
    """Test pgvector adapter with real database"""
    # Arrange
    store = PgVectorStore()
    doc = Document.objects.create(title="Test")
    chunk = DocumentChunk.objects.create(
        document=doc,
        content="Test content",
        embedding=[0.1] * 384
    )
    
    # Act
    results = store.search(
        query_embedding=[0.1] * 384,
        top_k=10
    )
    
    # Assert
    assert len(results) > 0
    assert results[0].chunk_id == chunk.id
```

## Adapter Best Practices

### ✅ DO
- Implement port interfaces completely
- Handle errors gracefully (don't let exceptions bubble)
- Add retry logic where appropriate
- Log important operations
- Validate inputs
- Use type hints

### ❌ DON'T
- Put business logic in adapters
- Access other adapters directly
- Ignore errors
- Use global state
- Leak infrastructure details to domain

## Error Handling

Adapters should translate infrastructure errors to domain errors:

```python
from apps.domain.models import DomainException

class OpenRouterLLM:
    def generate(self, messages):
        try:
            response = self.client.chat.completions.create(...)
            return response.choices[0].message.content
        except openai.RateLimitError as e:
            raise DomainException(f"LLM rate limit exceeded: {e}")
        except openai.APIError as e:
            raise DomainException(f"LLM API error: {e}")
```

## Migration from Current Code

Existing infrastructure code will be wrapped in adapters:

1. **Identify infrastructure code** (OpenRouter client, embedding code)
2. **Create adapter class** implementing port interface
3. **Wrap existing code** with minimal changes
4. **Add tests** validating adapter behavior
5. **Wire in container** for dependency injection

## Example Migration

**Before:**
```python
# apps/core/openrouter.py (global singleton)
openrouter_client = OpenRouterClient()

# Used directly in views
response = openrouter_client.generate_answer(messages)
```

**After:**
```python
# apps/adapters/llm/openrouter.py
class OpenRouterLLM:  # Implements ILLMProvider
    def generate(self, messages): ...

# apps/infrastructure/container.py
def create_llm_provider(config) -> ILLMProvider:
    return OpenRouterLLM(
        api_key=config['api_key'],
        model=config['model']
    )

# Domain service
class ChatService:
    def __init__(self, llm: ILLMProvider):  # Injected
        self._llm = llm
```