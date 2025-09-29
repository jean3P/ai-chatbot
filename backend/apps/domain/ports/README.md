# Ports (Interfaces)

## Purpose
Ports define **contracts** between the domain layer and infrastructure. They enable dependency inversion: domain defines what it needs, infrastructure provides it.

## Dependency Inversion Principle

```
┌─────────────────┐
│  Domain Layer   │  ← Defines interfaces (ports)
│  (high-level)   │  ← Contains business logic
└────────┬────────┘
         │ depends on
         ↓
┌─────────────────┐
│     Ports       │  ← Abstract interfaces (Protocol)
│  (contracts)    │  ← No implementation
└────────┬────────┘
         ↑ implements
         │
┌─────────────────┐
│   Adapters      │  ← Concrete implementations
│  (low-level)    │  ← Database, APIs, filesystems
└─────────────────┘
```

## Why Ports?

### Problem: Direct Dependencies
```python
# ❌ Domain directly depends on infrastructure
from apps.adapters.llm.openrouter import OpenRouterClient

class ChatService:
    def __init__(self):
        self.llm = OpenRouterClient()  # Tight coupling!
```

### Solution: Depend on Interface
```python
# ✅ Domain depends on abstract interface
from apps.domain.ports.llm import ILLMProvider

class ChatService:
    def __init__(self, llm: ILLMProvider):  # Depends on interface
        self._llm = llm  # Any implementation works
```

## Port Categories

### 1. LLM Providers (`llm.py`)
```python
class ILLMProvider(Protocol):
    """Interface for text generation"""
    def generate(self, messages: List[Dict]) -> str: ...
    def stream(self, messages: List[Dict]) -> Iterator[str]: ...
```

**Implementations:**
- `OpenRouterLLM` - OpenRouter API
- `AnthropicLLM` - Anthropic Claude
- `OpenAILLM` - OpenAI GPT
- `FakeLLM` - Testing

### 2. Embedding Providers (`embeddings.py`)
```python
class IEmbeddingProvider(Protocol):
    """Interface for vector embeddings"""
    def embed_batch(self, texts: List[str]) -> List[List[float]]: ...
    def embed_query(self, text: str) -> List[float]: ...
    def dimension(self) -> int: ...
```

**Implementations:**
- `SentenceTransformersEmbedding` - Local models
- `OpenRouterEmbedding` - API-based
- `FakeEmbedding` - Testing

### 3. Vector Stores (`retriever.py`)
```python
class IVectorStore(Protocol):
    """Interface for similarity search"""
    def search(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict]
    ) -> List[ChunkResult]: ...
    
    def add_vectors(
        self,
        chunk_ids: List[UUID],
        embeddings: List[List[float]],
        metadata: List[Dict]
    ) -> None: ...
```

**Implementations:**
- `NumPyVectorStore` - In-memory (dev/test)
- `PgVectorStore` - PostgreSQL (production)
- `FakeVectorStore` - Testing

### 4. Repositories (`repositories.py`)
```python
class IMessageRepository(Protocol):
    """Interface for message persistence"""
    def save(self, message: Message) -> Message: ...
    def get(self, id: UUID) -> Optional[Message]: ...
    def list_by_conversation(self, conv_id: UUID) -> List[Message]: ...
```

**Implementations:**
- `DjangoMessageRepository` - ORM-based
- `InMemoryMessageRepository` - Testing

### 5. Document Parsers (`parser.py`)
```python
class IDocumentParser(Protocol):
    """Interface for extracting text from files"""
    def parse(self, file_path: str) -> DocumentContent: ...
    def supports(self, file_type: str) -> bool: ...
```

**Implementations:**
- `PyMuPDFParser` - PDF extraction
- `PDFPlumberParser` - Backup PDF
- `FakeParser` - Testing

## Python Protocol vs ABC

We use `typing.Protocol` for structural typing:

```python
from typing import Protocol, List

class ILLMProvider(Protocol):
    """Duck typing: any class with these methods works"""
    def generate(self, messages: List[Dict]) -> str: ...
```

**Benefits:**
- No inheritance required
- Lighter weight than ABC
- Better type checking (mypy)
- More Pythonic

## Testing with Fakes

Ports enable pure unit testing:

```python
class FakeLLM:
    """Test double for LLM provider"""
    def __init__(self, response: str = "test response"):
        self.response = response
        self.generate_called = False
    
    def generate(self, messages: List[Dict]) -> str:
        self.generate_called = True
        return self.response

# Test using fake
def test_chat_service_calls_llm():
    fake_llm = FakeLLM(response="Hello")
    service = ChatService(llm=fake_llm)
    
    result = service.answer("Hi")
    
    assert fake_llm.generate_called is True
    assert result.content == "Hello"
```

## Port Files to Create

1. `llm.py` - Text generation interfaces
2. `embeddings.py` - Vector embedding interfaces
3. `retriever.py` - Similarity search interfaces
4. `repositories.py` - Data persistence interfaces
5. `parser.py` - Document parsing interfaces

## Best Practices

### ✅ DO
- Keep interfaces small and focused
- Use type hints everywhere
- Document expected behavior
- Define clear contracts

### ❌ DON'T
- Add implementation in ports
- Leak infrastructure details
- Create "god interfaces"
- Skip documentation

## References
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Python Protocols (PEP 544)](https://peps.python.org/pep-0544/)
- [Hexagonal Architecture Ports](https://alistair.cockburn.us/hexagonal-architecture/)