# Repository Adapters

## Purpose
Repository adapters implement data persistence ports, providing access to stored data.

## Interface Examples

```python
class IMessageRepository(Protocol):
    def save(self, message: Message) -> Message: ...
    def get(self, id: UUID) -> Optional[Message]: ...
    def list_by_conversation(self, conv_id: UUID) -> List[Message]: ...

class IConversationRepository(Protocol):
    def save(self, conversation: Conversation) -> Conversation: ...
    def get(self, id: UUID) -> Optional[Conversation]: ...
    def list_by_user(self, user_id: UUID) -> List[Conversation]: ...
```

## Implementations

### 1. Django ORM Repositories
- **Storage**: PostgreSQL via Django ORM
- **Use case**: Production

**Example:**
```python
class DjangoMessageRepository:
    def save(self, message: Message) -> Message:
        orm_message = ORMMessage.objects.create(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role.value,
            content=message.content,
            metadata=message.metadata
        )
        return self._to_domain(orm_message)
    
    def get(self, id: UUID) -> Optional[Message]:
        try:
            orm_message = ORMMessage.objects.get(id=id)
            return self._to_domain(orm_message)
        except ORMMessage.DoesNotExist:
            return None
    
    def _to_domain(self, orm_message) -> Message:
        """Convert ORM model to domain model"""
        return Message(
            id=orm_message.id,
            conversation_id=orm_message.conversation_id,
            role=MessageRole(orm_message.role),
            content=orm_message.content,
            metadata=orm_message.metadata,
            created_at=orm_message.created_at
        )
```

### 2. In-Memory Repositories
- **Storage**: Python dict
- **Use case**: Testing

**Example:**
```python
class InMemoryMessageRepository:
    def __init__(self):
        self._messages = {}
    
    def save(self, message: Message) -> Message:
        self._messages[message.id] = message
        return message
    
    def get(self, id: UUID) -> Optional[Message]:
        return self._messages.get(id)
```

## Testing

```python
def test_django_message_repository():
    """Integration test with database"""
    repo = DjangoMessageRepository()
    
    message = Message(
        role=MessageRole.USER,
        content="Test message"
    )
    
    saved = repo.save(message)
    retrieved = repo.get(saved.id)
    
    assert retrieved.id == saved.id
    assert retrieved.content == "Test message"

def test_inmemory_repository():
    """Unit test with fake"""
    repo = InMemoryMessageRepository()
    
    message = Message(content="Test")
    saved = repo.save(message)
    
    assert repo.get(saved.id) == message
```

## Migration Notes

Repositories wrap existing Django models:
- Create thin wrapper around ORM
- Convert between domain and ORM models
- Keep ORM knowledge in repositories only
```