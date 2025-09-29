# Infrastructure Layer

## Purpose
Infrastructure layer provides cross-cutting concerns and wires together the application using dependency injection.

## Components

### 1. Container (`container.py`)
Dependency injection container that creates and wires together:
- Domain services
- Adapters
- Configuration

**Example:**
```python
from apps.infrastructure.container import create_chat_service

# In view/consumer
chat_service = create_chat_service()
answer = chat_service.answer_question(...)
```

### 2. Configuration (`config.py`)
Environment-specific configuration:
- Test: Fake adapters, fast
- Development: Real adapters, permissive
- Production: Optimized, strict

### 3. Tasks (`tasks.py` - Future)
Celery background jobs:
- Document processing
- Embedding generation
- Evaluation experiments

## Dependency Injection Pattern

Simple factory pattern (no framework needed):

```python
def create_chat_service(config: Dict = None) -> ChatService:
    """Factory function creating fully wired ChatService"""
    config = config or get_config()
    
    # Create adapters
    llm = create_llm_provider(config['llm'])
    embedder = create_embedding_provider(config['embedding'])
    retriever = create_vector_store(config['retriever'])
    
    # Create strategy
    strategy = BaselineStrategy(
        retriever=retriever,
        llm=llm,
        prompt_template=PromptTemplate(version="v1.0")
    )
    
    # Create repositories
    msg_repo = DjangoMessageRepository()
    conv_repo = DjangoConversationRepository()
    
    # Wire service
    return ChatService(
        rag_strategy=strategy,
        message_repo=msg_repo,
        conversation_repo=conv_repo
    )
```

## Configuration Structure

```python
CONFIG = {
    'test': {
        'llm': {'type': 'fake'},
        'embedding': {'type': 'fake', 'dimension': 384},
        'retriever': {'type': 'numpy'}
    },
    'development': {
        'llm': {'type': 'openrouter', 'model': 'gpt-4o-mini'},
        'embedding': {'type': 'sentence_transformers'},
        'retriever': {'type': 'numpy'}
    },
    'production': {
        'llm': {'type': 'openrouter', 'model': 'gpt-4o-mini'},
        'embedding': {'type': 'sentence_transformers'},
        'retriever': {'type': 'pgvector'}
    }
}
```

## Benefits of Simple DI

### ✅ Advantages
- No magic (explicit construction)
- Easy to understand
- Easy to debug
- No framework lock-in
- Type-safe

### ❌ What We Avoid
- Complex DI frameworks
- Auto-wiring magic
- Hidden dependencies
- Reflection overhead

## Testing Infrastructure

```python
def test_container_creates_service():
    """Test dependency wiring"""
    config = TEST_CONFIG
    service = create_chat_service(config)
    
    assert isinstance(service, ChatService)
    assert isinstance(service._rag_strategy, BaselineStrategy)
```

## Environment Detection

The container uses `ENVIRONMENT` env var to determine configuration:

```bash
# Test
export ENVIRONMENT=test
python manage.py test

# Development (default)
export ENVIRONMENT=development
python manage.py runserver

# Production
export ENVIRONMENT=production
gunicorn config.wsgi
```

## Configuration Override

Override config for specific use cases:

```python
# Use test config in unit tests
config = TEST_CONFIG
service = create_chat_service(config)

# Use custom config for experiments
custom_config = DEVELOPMENT_CONFIG.copy()
custom_config['llm']['model'] = 'gpt-4o'
service = create_chat_service(custom_config)
```

## Migration Strategy

1. **Create container** with factories for each adapter type
2. **Update views** to use container instead of global singletons
3. **Test** that wiring works correctly
4. **Deploy** with feature flag
5. **Remove** old global singletons

## Best Practices

### ✅ DO
- Keep factories simple
- Use type hints
- Validate configuration
- Document dependencies
- Test wiring

### ❌ DON'T
- Add business logic in container
- Create circular dependencies
- Use global state
- Auto-wire via reflection
- Skip validation