# Domain Layer

## Overview
The domain layer contains the **pure business logic** of the RAG chatbot system. This layer is completely independent of frameworks, databases, and external services.

## Design Principles

### 1. Framework Independence
- No Django imports
- No database access
- No HTTP/WebSocket code
- Pure Python only

### 2. Dependency Rule
- Domain depends on **nothing**
- All dependencies point **inward** to domain
- Adapters depend on domain (via ports)
- API layer depends on domain services

### 3. Testability
- 100% unit testable without infrastructure
- Tests run in milliseconds
- No mocks needed for domain logic
- Use fakes for ports (test doubles)

## Structure

```
domain/
├── services/        # Application services (orchestration)
├── strategies/      # RAG method implementations
├── ports/           # Interface definitions (dependency inversion)
├── prompts/         # Prompt templates (versioned)
└── models.py        # Value objects and entities
```

## What Belongs Here?

### ✅ YES - Domain Layer
- RAG retrieval strategies
- Prompt building logic
- Citation extraction rules
- Business validation rules
- Domain events
- Value objects

### ❌ NO - Infrastructure Layer
- Django models/ORM
- HTTP request handlers
- Database queries
- External API clients
- File I/O operations
- WebSocket handlers

## Example: Good Domain Code

```python
# ✅ Good: Pure Python, testable
class BaselineRagStrategy:
    def __init__(self, retriever: IRetriever, llm: ILLMProvider):
        self._retriever = retriever
        self._llm = llm
    
    def generate_answer(self, query: str, history: List[Message]) -> Answer:
        chunks = self._retriever.search(query, limit=10)
        prompt = self._build_prompt(query, chunks, history)
        response = self._llm.generate(prompt)
        citations = self._extract_citations(response, chunks)
        return Answer(content=response, citations=citations)
```

## Example: Bad Domain Code

```python
# ❌ Bad: Django dependency, not testable
from apps.chat.models import Message  # Django import!

def generate_answer(query: str):
    messages = Message.objects.filter(...)  # Database call!
    # Business logic mixed with infrastructure
```

## Testing Strategy

Domain layer should have **80%+ test coverage** with pure unit tests:

```python
def test_baseline_strategy_retrieves_relevant_chunks():
    # Arrange: Use fakes, no infrastructure
    fake_retriever = FakeRetriever(results=[...])
    fake_llm = FakeLLM(response="Answer")
    strategy = BaselineRagStrategy(fake_retriever, fake_llm)
    
    # Act: Pure function call
    answer = strategy.generate_answer("How to install?", history=[])
    
    # Assert: Verify logic
    assert len(answer.citations) > 0
    assert "install" in answer.content.lower()
```

## Migration Strategy

Existing code will be gradually refactored into this layer:
1. Extract logic from views → services
2. Create port interfaces for dependencies
3. Implement adapters for ports
4. Wire together in container
5. Delete old code

## References
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Ports and Adapters Pattern](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/)
```