# Application Services

## Purpose
Application services orchestrate domain logic to fulfill use cases. They coordinate between domain strategies and infrastructure adapters through port interfaces.

## Responsibilities

### ✅ What Services DO
- Orchestrate use cases (e.g., "answer user question")
- Define transaction boundaries
- Coordinate multiple domain objects
- Call port interfaces for I/O
- Handle application-level errors
- Convert between domain and DTO models

### ❌ What Services DON'T DO
- Contain business logic (that's in strategies/models)
- Know about databases (use repository ports)
- Know about HTTP (that's in API layer)
- Directly call external APIs (use adapter ports)

## Example Structure

```python
class ChatService:
    """Orchestrates the chat conversation flow"""
    
    def __init__(
        self,
        rag_strategy: IRagStrategy,
        message_repo: IMessageRepository,
        conversation_repo: IConversationRepository
    ):
        self._rag_strategy = rag_strategy
        self._message_repo = message_repo
        self._conversation_repo = conversation_repo
    
    def answer_question(
        self,
        conversation_id: UUID,
        query: str,
        language: str
    ) -> AnswerResult:
        """
        Use case: User asks a question and receives an answer
        
        Steps:
        1. Load conversation history
        2. Generate answer using RAG strategy
        3. Save user message
        4. Save assistant message
        5. Return result
        """
        # Orchestration logic here
        pass
```

## Testing Strategy

Services should be tested with **fake adapters** (test doubles):

```python
def test_chat_service_saves_messages():
    # Arrange
    fake_strategy = FakeRagStrategy(response="Answer")
    fake_msg_repo = FakeMessageRepository()
    fake_conv_repo = FakeConversationRepository()
    
    service = ChatService(fake_strategy, fake_msg_repo, fake_conv_repo)
    
    # Act
    result = service.answer_question(
        conversation_id=UUID("..."),
        query="How to install?",
        language="en"
    )
    
    # Assert
    assert fake_msg_repo.save_called == 2  # user + assistant
    assert result.success is True
```

## Planned Services

- `ChatService` - Handle conversations and message flow
- `DocumentService` - Process document uploads
- `EvaluationService` - Run experiments and A/B tests

## Dependencies

Services receive dependencies via **constructor injection**:
- No global singletons
- No service locator
- Explicit dependencies
- Easy to test

## Transaction Management

Services define transaction boundaries:

```python
def answer_question(self, ...):
    with self._transaction_manager.begin():
        # All or nothing
        user_msg = self._message_repo.save(...)
        answer = self._rag_strategy.generate(...)
        assistant_msg = self._message_repo.save(...)
        return AnswerResult(...)
```